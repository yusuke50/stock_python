import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TODAY = date.today()

RS_MIN_PCT = 70
PIVOT_LOOKBACK = 25
NEAR_PIVOT_RATIO = 0.95
BREAKOUT_VOL_RATIO = 1.4
EPS_GROWTH_MIN = 0.25
REV_GROWTH_MIN = 0.25
FUND_WORKERS = 8

# ETF codes (00xxx) have no quarterly income statement; calc-tw.py skips them too.
ETF_PATTERN = re.compile(r"^00\w+\.TWO?$")


def load_tickers():
    with open(os.path.join(BASE_DIR, "stock-list-tw.txt"), "r", encoding="utf-8") as f:
        tickers = [line.strip() for line in f if line.strip()]
    return [t for t in tickers if not ETF_PATTERN.match(t)]


def download_prices(tickers):
    try:
        return yf.download(
            tickers,
            period="2y",
            interval="1d",
            auto_adjust=True,
            group_by="ticker",
            threads=True,
            progress=False,
        )
    except Exception as e:
        # Exit non-zero so daily.bat stops the chain (the || guard).
        print(f"Download failed: {type(e).__name__} {e}")
        raise SystemExit(1)


def get_frame(raw, ticker):
    df = raw[ticker]
    df = df.dropna(subset=["Close"])
    # Drop today's bar: the session is not finished yet.
    return df[df.index.date < TODAY]


def perf(close, days):
    return close.iloc[-1] / close.iloc[-1 - days] - 1


def trend_metrics(df):
    close = df["Close"]
    if len(close) < 260:
        raise ValueError(f"only {len(close)} bars")

    last = float(close.iloc[-1])
    sma50 = close.rolling(50).mean()
    sma150 = close.rolling(150).mean()
    sma200 = close.rolling(200).mean()
    last252 = close.iloc[-252:]
    low52 = float(last252.min())
    high52 = float(last252.max())
    # IBD-style weighted momentum: the last 3 months count double.
    score = (
        0.4 * perf(close, 63)
        + 0.2 * perf(close, 126)
        + 0.2 * perf(close, 189)
        + 0.2 * perf(close, 251)
    )

    criteria = {
        "C1": last > sma150.iloc[-1] and last > sma200.iloc[-1],
        "C2": sma150.iloc[-1] > sma200.iloc[-1],
        "C3": sma200.iloc[-1] > sma200.iloc[-22],
        "C4": sma50.iloc[-1] > sma150.iloc[-1] and sma50.iloc[-1] > sma200.iloc[-1],
        "C5": last > sma50.iloc[-1],
        "C6": last >= 1.30 * low52,
        "C7": last >= 0.75 * high52,
    }
    return {"close": last, "high52": high52, "rs_raw": score, **criteria}


def vcp_metrics(df):
    # Base: the 25 bars before the test bar (the last completed session).
    base = df.iloc[-(PIVOT_LOOKBACK + 1):-1]
    test = df.iloc[-1]
    pivot = float(base["High"].max())

    seg1, seg2, seg3 = base.iloc[0:8], base.iloc[8:16], base.iloc[16:]

    def depth(seg):
        hi = seg["High"].max()
        return (hi - seg["Low"].min()) / hi

    d1, d2, d3 = depth(seg1), depth(seg2), depth(seg3)
    contracting = d1 > d2 > d3

    vol = df["Volume"]
    vol50 = float(vol.iloc[-51:-1].mean())
    vol10 = float(vol.iloc[-11:-1].mean())
    dry_up = vol10 < vol50

    close = float(test["Close"])
    breakout_ratio = float(test["Volume"]) / vol50 if vol50 > 0 else 0.0

    if close > pivot and breakout_ratio >= BREAKOUT_VOL_RATIO:
        status = "BREAKOUT"
    elif NEAR_PIVOT_RATIO * pivot <= close <= pivot:
        status = "NEAR PIVOT"
    else:
        status = None

    return {
        "vcp_ok": bool(contracting and dry_up),
        "pivot": pivot,
        "status": status,
        "breakout_ratio": breakout_ratio,
    }


def fundamentals(ticker):
    q = yf.Ticker(ticker).quarterly_income_stmt
    if q is None or q.empty or q.shape[1] < 5:
        raise ValueError("missing quarterly statements")
    q = q.sort_index(axis=1, ascending=False)

    def yoy(row):
        if row not in q.index:
            raise ValueError(f"missing {row}")
        cur = q.loc[row].iloc[0]
        prev = q.loc[row].iloc[4]
        if pd.isna(cur) or pd.isna(prev):
            raise ValueError(f"missing {row} value")
        if prev <= 0:
            return None  # Growth is not defined on a non-positive base.
        return float(cur / prev - 1)

    return yoy("Diluted EPS"), yoy("Total Revenue")


def main():
    tickers = load_tickers()
    raw = download_prices(tickers)

    errors = []
    tech_rows = {}
    for t in tickers:
        try:
            df = get_frame(raw, t)
            tech_rows[t] = {"df": df, **trend_metrics(df)}
        except Exception as e:
            errors.append(f"{t} failed (technical: {type(e).__name__} {e}).")

    # C8: RS percentile within the list.
    rs = pd.Series({t: r["rs_raw"] for t, r in tech_rows.items()})
    rs_pct = rs.rank(pct=True) * 100
    for t, r in tech_rows.items():
        r["rs_pct"] = float(rs_pct[t])
        r["C8"] = r["rs_pct"] >= RS_MIN_PCT

    trend_pass = {
        t: r for t, r in tech_rows.items()
        if all(r[k] for k in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"))
    }

    candidates = {}
    for t, r in trend_pass.items():
        v = vcp_metrics(r["df"])
        if v["vcp_ok"] and v["status"] is not None:
            candidates[t] = {**r, **v}

    def fund_for(t):
        try:
            return t, fundamentals(t), None
        except Exception as e:
            return t, None, f"{t} failed (fundamentals: {type(e).__name__} {e})."

    buy = []
    with ThreadPoolExecutor(max_workers=FUND_WORKERS) as pool:
        for t, fund, err in pool.map(fund_for, list(candidates)):
            if err:
                errors.append(err)
                continue
            eps, rev = fund
            if eps is None or rev is None:
                continue
            if eps < EPS_GROWTH_MIN or rev < REV_GROWTH_MIN:
                continue
            c = candidates[t]
            buy.append((c["rs_pct"], t, c, eps, rev))

    buy.sort(reverse=True)
    buy_lines = [
        f"{t}, Close: {c['close']:.2f}, Pivot: {c['pivot']:.2f}, {c['status']}, "
        f"Vol: {c['breakout_ratio']:.2f}x, EPS YoY: {eps * 100:.1f}%, "
        f"Rev YoY: {rev * 100:.1f}%, RS: {c['rs_pct']:.0f}"
        for _, t, c, eps, rev in buy
    ]

    print(f"tickers: {len(tickers)}, technical ok: {len(tech_rows)}")
    print(f"trend template pass: {len(trend_pass)}, VCP + pivot candidates: {len(candidates)}")
    print(f"buy list: {len(buy)}, errors: {len(errors)}")

    # Same file that calc-tw.py writes. Append so calc-tw.py output is kept.
    path = os.path.join(BASE_DIR, "list", str(TODAY.year), f"Q{(TODAY.month - 1) // 3 + 1}")
    os.makedirs(path, exist_ok=True)
    final_file_name = os.path.join(path, f"final-list-{TODAY}.txt")
    with open(final_file_name, "a", encoding="utf-8") as f:
        f.write("\n--------------\n")
        f.write(f"{time.ctime(time.time())} TW Minervini SEPA Buy List\n")
        f.write("--------------\n")
        f.write("\n".join(buy_lines))
        f.write("\n")
        f.write("--------------\n")
        f.write("\n".join(errors))
        f.write("\n")


if __name__ == "__main__":
    main()
