"""Minervini-style sell rules for one holding.

Pure logic only: no network and no file I/O. The caller passes OHLCV bars.
Messages use ASCII operators so they print on any Windows console code page.
"""
import pandas as pd

SELL = "SELL"  # exit the position
TRIM = "TRIM"  # reduce the position
WARN = "WARN"  # watch closely

# Float tolerance for threshold comparisons. Prices like 1.10 and 2.05 do not
# divide exactly in binary floating point, so 10% and 20% gains need this.
EPS = 1e-9


class Alert:
    def __init__(self, level, rule, message):
        self.level = level
        self.rule = rule
        self.message = message

    def __repr__(self):
        return f"Alert({self.level}, {self.rule}, {self.message})"


def evaluate(symbol, avg_cost, buy_date, bars, cfg, initial_stop_pct=None):
    """Return (alerts, stop_price, stop_type) for the last bar in `bars`.

    bars: DataFrame with Open, High, Low, Close, Volume columns.
          Index is an ascending, tz-naive DatetimeIndex. The last row is the
          evaluation day.
    cfg: threshold dict. See sell-config.json.
    initial_stop_pct: per-position override of cfg["initial_stop_pct"].
    """
    stop_pct = initial_stop_pct if initial_stop_pct is not None else cfg["initial_stop_pct"]
    avg_cost = float(avg_cost)
    if bars.empty:
        raise ValueError(f"{symbol}: no price bars")
    if bars[["Close", "Low", "Volume"]].iloc[-1].isna().any():
        raise ValueError(f"{symbol}: last bar is missing Close, Low or Volume")
    bars = bars.dropna(subset=["Close"])
    since = bars[bars.index >= pd.Timestamp(buy_date)]
    if since.empty:
        raise ValueError(f"{symbol}: no bars on or after buy_date {buy_date}")

    last = bars.iloc[-1]
    close, low, vol = float(last["Close"]), float(last["Low"]), float(last["Volume"])
    close_s = bars["Close"]
    sma50 = close_s.rolling(50).mean().iloc[-1]
    sma200 = close_s.rolling(200).mean().iloc[-1]
    ema10_s = close_s.ewm(span=10, adjust=False).mean()
    avg_vol50 = bars["Volume"].iloc[-51:-1].mean()  # prior 50 bars, excludes today
    has_vol_avg = pd.notna(avg_vol50) and avg_vol50 > 0

    gain = close / avg_cost - 1
    peak_close = float(since["Close"].max())
    peak_gain = peak_close / avg_cost - 1
    days_held = len(since)

    # Stop ladder. Stop only moves up. Protection uses the highest close
    # since buy, so the stop stays at cost after the trigger is reached.
    stop = avg_cost * (1 - stop_pct)
    stop_type = "初始止損"
    protect_at = avg_cost * (1 + cfg["protect_multiple"] * stop_pct)
    if peak_close >= protect_at:
        stop = avg_cost
        stop_type = "保本止損"

    alerts = []

    # 1. Hard stop
    if close <= stop:
        alerts.append(Alert(SELL, stop_type, f"收盤 {close:.2f} <= 止損價 {stop:.2f}"))
    elif low <= stop:
        alerts.append(Alert(WARN, stop_type, f"盤中低 {low:.2f} 觸及止損價 {stop:.2f}，待收盤確認"))

    # 2. Trailing exits (trend breaks)
    if pd.notna(sma50) and close < sma50:
        if has_vol_avg and vol >= cfg["heavy_vol_mult"] * avg_vol50:
            alerts.append(Alert(SELL, "放量跌破50MA", f"收盤 {close:.2f} < 50MA {sma50:.2f}，量 {vol / avg_vol50:.1f} 倍均量"))
        else:
            alerts.append(Alert(WARN, "跌破50MA", f"收盤 {close:.2f} < 50MA {sma50:.2f}，量未放大"))

    if len(bars) >= 2 and (close_s.iloc[-2:] < ema10_s.iloc[-2:]).all():
        alerts.append(Alert(WARN, "連續2日低於EMA10", f"EMA10 {ema10_s.iloc[-1]:.2f}"))

    if len(bars) >= 11:
        prior_low = close_s.iloc[-11:-1].min()
        if close < prior_low:
            alerts.append(Alert(WARN, "跌破近10日低點", f"收盤 {close:.2f} < 前10日最低收盤 {prior_low:.2f}"))

    if pd.notna(sma200) and close < sma200:
        if has_vol_avg and vol >= cfg["heavy_vol_mult"] * avg_vol50:
            alerts.append(Alert(SELL, "放量跌破200MA", f"收盤 {close:.2f} < 200MA {sma200:.2f}，Stage 2 結束"))
        else:
            alerts.append(Alert(WARN, "跌破200MA", f"收盤 {close:.2f} < 200MA {sma200:.2f}，量未放大"))

    # 3. Trailing profit lock. Arms at lock_min_gain. Lock gain = max(min, ratio * peak gain),
    # so the lock only moves up. Trims only. Drawdown trim applies only above lock_drawdown_min_gain.
    if peak_gain + EPS >= cfg["lock_min_gain"]:
        lock_gain = max(cfg["lock_min_gain"], cfg["lock_peak_ratio"] * peak_gain)
        lock_price = avg_cost * (1 + lock_gain)
        if close <= lock_price + EPS * avg_cost:
            alerts.append(Alert(TRIM, "移動鎖利", f"損益 {gain:.1%} <= 鎖利點 {lock_gain:.1%}（最高損益 {peak_gain:.1%}）"))
        drawdown = 1 - close / peak_close
        if peak_gain - EPS > cfg["lock_drawdown_min_gain"] and drawdown + EPS >= cfg["lock_drawdown_pct"]:
            alerts.append(Alert(TRIM, "最高點回撤", f"自最高收盤 {peak_close:.2f} 回撤 {drawdown:.1%}"))

    # 4. Sell into strength (trim)
    if gain >= cfg["profit_take_pct"]:
        alerts.append(Alert(TRIM, "獲利減碼", f"獲利 {gain:.1%} >= {cfg['profit_take_pct']:.0%}，可減碼一半"))

    if len(bars) >= 11 and has_vol_avg:
        day_ret = close / close_s.iloc[-2] - 1
        run_ret = close / close_s.iloc[-11] - 1
        recent_day_rets = close_s.pct_change(fill_method=None).iloc[-10:]
        vol_ratio = vol / avg_vol50
        if (
            run_ret >= cfg["climax_run_pct"]
            and vol_ratio >= cfg["climax_vol_mult"]
            and day_ret >= cfg["climax_day_pct"]
            and day_ret >= recent_day_rets.max()
        ):
            alerts.append(Alert(TRIM, "高潮頂", f"10日漲 {run_ret:.1%}，今日漲 {day_ret:.1%}（10日最大），量 {vol_ratio:.1f} 倍均量"))

    if pd.notna(sma50) and close / sma50 - 1 >= cfg["extension_pct"]:
        alerts.append(Alert(TRIM, "乖離過大", f"離50MA {close / sma50 - 1:.1%}"))

    # 5. Time stop
    if days_held >= cfg["time_stop_days"] and gain < cfg["time_stop_min_gain"]:
        alerts.append(Alert(WARN, "時間止損", f"持有 {days_held} 個交易日，獲利 {gain:.1%} 未達 {cfg['time_stop_min_gain']:.0%}"))

    return alerts, stop, stop_type
