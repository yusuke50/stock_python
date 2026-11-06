"""Daily sell-alert monitor for manually recorded holdings (TW and US).

Reads holdings.csv and sell-config.json, fetches daily bars from yfinance,
applies sell_rules.evaluate, and writes positions/alerts-YYYY-MM-DD.txt.
Usage: python positions-monitor.py [holdings.csv path]
"""
import csv
import json
import math
import os
import sys
import time
from datetime import date

import yfinance as yf

import sell_rules

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOLDINGS_PATH = os.path.join(BASE_DIR, "holdings.csv")
CONFIG_PATH = os.path.join(BASE_DIR, "sell-config.json")
OUT_DIR = os.path.join(BASE_DIR, "positions")
MARKET_TITLES = {"TW": "台股", "US": "美股"}
OWNERS = ("L", "B", "P")
REQUEST_PAUSE_SEC = 0.5


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def market_config(raw, market):
    cfg = dict(raw["defaults"])
    cfg.update(raw.get("markets", {}).get(market, {}))
    return cfg


def positive_number(value, name):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be a positive number, got {value!r}")
    return number


REQUIRED_COLUMNS = ("owner", "symbol", "market", "shares", "avg_cost", "buy_date")


def parse_row(r):
    owner = (r.get("owner") or "").strip().upper()
    if owner not in OWNERS:
        raise ValueError(f"owner must be one of {', '.join(OWNERS)}, got {owner!r}")
    market = (r.get("market") or "").strip().upper()
    if market not in MARKET_TITLES:
        raise ValueError(f"market must be TW or US, got {market!r}")
    override = (r.get("initial_stop_pct") or "").strip()
    stop_pct = None
    if override:
        stop_pct = float(override)
        if not math.isfinite(stop_pct) or not 0 < stop_pct < 1:
            raise ValueError(f"initial_stop_pct must be between 0 and 1, got {override!r}")
    buy_date = (r.get("buy_date") or "").strip()
    try:
        date.fromisoformat(buy_date)
    except ValueError:
        raise ValueError(f"buy_date must be YYYY-MM-DD, got {buy_date!r}")
    return {
        "owner": owner,
        "symbol": r["symbol"].strip(),
        "market": market,
        "shares": positive_number(r["shares"], "shares"),
        "avg_cost": positive_number(r["avg_cost"], "avg_cost"),
        "buy_date": buy_date,
        "initial_stop_pct": stop_pct,
    }


def load_holdings(path):
    """Return (holdings, errors). One bad row does not stop the other rows."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"holdings.csv header is missing columns: {', '.join(missing)}")
        rows = [r for r in reader if (r.get("symbol") or "").strip()]
    holdings, errors = [], []
    for r in rows:
        try:
            holdings.append(parse_row(r))
        except Exception as e:
            errors.append(f"{r['symbol'].strip()}  ROW ERROR: {e}")
    return holdings, errors


def clean_bars(df):
    """Keep only complete bars. Yahoo can return a current-day row with volume but no prices."""
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    return df.dropna(how="any")


def fetch_bars(symbol):
    df = yf.Ticker(symbol).history(period="2y", auto_adjust=True)
    if df.empty:
        raise ValueError("no price data from yfinance")
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = clean_bars(df)
    if df.empty:
        raise ValueError("no complete price bars from yfinance")
    return df


def format_block(pos, bars, alerts, stop, stop_type):
    close = float(bars["Close"].iloc[-1])
    gain = close / pos["avg_cost"] - 1
    bar_date = bars.index[-1].date().isoformat()
    lines = [
        f"{pos['symbol']}  bar {bar_date}  close {close:.2f}  cost {pos['avg_cost']:.2f}  "
        f"P/L {gain:+.1%}  stop {stop:.2f} ({stop_type})",
    ]
    if not alerts:
        lines.append("  (no alert)")
    for a in alerts:
        lines.append(f"  [{a.level}] {a.rule}: {a.message}")
    return lines


def run(holdings_path):
    raw = load_config()
    holdings, row_errors = load_holdings(holdings_path)
    sections = {(o, m): [] for o in OWNERS for m in MARKET_TITLES}

    for pos in holdings:
        key = (pos["owner"], pos["market"])
        try:
            if pos["market"] == "TW" and not pos["symbol"].endswith((".TW", ".TWO")):
                raise ValueError("TW symbol needs .TW or .TWO suffix")
            bars = fetch_bars(pos["symbol"])
            cfg = market_config(raw, pos["market"])
            alerts, stop, stop_type = sell_rules.evaluate(
                pos["symbol"], pos["avg_cost"], pos["buy_date"], bars, cfg,
                initial_stop_pct=pos["initial_stop_pct"],
            )
            sections[key].extend(format_block(pos, bars, alerts, stop, stop_type))
        except Exception as e:
            sections[key].append(f"{pos['symbol']}  ERROR: {e}")
        time.sleep(REQUEST_PAUSE_SEC)

    today = date.today().isoformat()
    out_lines = [f"Position sell alerts {today}", ""]
    for owner in OWNERS:
        for market, title in MARKET_TITLES.items():
            if not sections[(owner, market)]:
                continue
            out_lines.append(f"==== 持股人 {owner} / {title} ({market}) ====")
            out_lines.extend(sections[(owner, market)])
            out_lines.append("")
    if row_errors:
        out_lines.append("==== 格式錯誤 (holdings.csv) ====")
        out_lines.extend(row_errors)
        out_lines.append("")

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"alerts-{today}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

    sys.stdout.reconfigure(errors="replace")
    print("\n".join(out_lines))
    print(f"Written: {out_path}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else HOLDINGS_PATH)
