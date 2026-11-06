"""Unit tests for sell_rules.evaluate. Run: python -m unittest test_sell_rules"""
import importlib.util
import json
import os
import tempfile
import unittest

import pandas as pd

import sell_rules

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sell-config.json")


def make_cfg():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return dict(json.load(f)["defaults"])


def make_bars(closes, vols=None, lows=None):
    n = len(closes)
    idx = pd.bdate_range("2025-01-01", periods=n)
    df = pd.DataFrame({
        "Open": closes,
        "High": closes,
        "Low": closes if lows is None else lows,
        "Close": closes,
        "Volume": vols if vols is not None else [1_000_000] * n,
    }, index=idx)
    return df


def rules(alerts):
    return {(a.level, a.rule) for a in alerts}


class InitialAndProtectedStopTest(unittest.TestCase):
    def test_no_stop_alert_above_initial_stop(self):
        closes = [100.0] * 60
        bars = make_bars(closes)
        alerts, stop, stop_type = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertAlmostEqual(stop, 90.0)
        self.assertEqual(stop_type, "初始止損")
        self.assertFalse(any(a.rule in ("初始止損", "保本止損") for a in alerts))

    def test_initial_stop_hit_sells(self):
        closes = [100.0] * 59 + [89.0]
        bars = make_bars(closes)
        alerts, stop, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("SELL", "初始止損"), rules(alerts))

    def test_intraday_low_below_stop_warns_only(self):
        closes = [100.0] * 59 + [95.0]
        lows = [100.0] * 59 + [89.0]
        bars = make_bars(closes, lows=lows)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("WARN", "初始止損"), rules(alerts))
        self.assertNotIn(("SELL", "初始止損"), rules(alerts))

    def test_protected_stop_moves_to_cost_after_3x_stop_gain(self):
        # Peak close 131 >= 100 * (1 + 3 * 0.10) = 130, so stop becomes cost.
        closes = [100.0] * 50 + [131.0, 120.0, 99.0]
        bars = make_bars(closes)
        alerts, stop, stop_type = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertAlmostEqual(stop, 100.0)
        self.assertEqual(stop_type, "保本止損")
        self.assertIn(("SELL", "保本止損"), rules(alerts))

    def test_stop_does_not_drop_back_after_protection(self):
        closes = [100.0] * 50 + [131.0, 110.0]
        bars = make_bars(closes)
        _, stop, stop_type = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertAlmostEqual(stop, 100.0)
        self.assertEqual(stop_type, "保本止損")

    def test_protection_not_triggered_below_3x_stop_gain(self):
        closes = [100.0] * 50 + [125.0, 110.0]
        bars = make_bars(closes)
        _, stop, stop_type = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertAlmostEqual(stop, 90.0)
        self.assertEqual(stop_type, "初始止損")

    def test_per_position_stop_override(self):
        closes = [100.0] * 60
        bars = make_bars(closes)
        _, stop, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg(), initial_stop_pct=0.08)
        self.assertAlmostEqual(stop, 92.0)


class TrailingAndTrendTest(unittest.TestCase):
    def test_break_50ma_on_heavy_volume_sells(self):
        closes = [100.0] * 59 + [95.0]
        vols = [1_000_000] * 59 + [2_000_000]
        bars = make_bars(closes, vols=vols)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("SELL", "放量跌破50MA"), rules(alerts))

    def test_break_50ma_on_normal_volume_warns(self):
        closes = [100.0] * 59 + [95.0]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("WARN", "跌破50MA"), rules(alerts))
        self.assertNotIn(("SELL", "放量跌破50MA"), rules(alerts))


class TrimTest(unittest.TestCase):
    def test_trim_at_25_percent_gain(self):
        closes = [100.0] * 59 + [126.0]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("TRIM", "獲利減碼"), rules(alerts))

    def test_climax_top_detected(self):
        closes = [100.0] * 50 + [102, 104, 106, 108, 110, 112, 114, 116, 118, 126]
        vols = [1_000_000] * 59 + [3_000_000]
        bars = make_bars(closes, vols=vols)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("TRIM", "高潮頂"), rules(alerts))

    def test_no_climax_without_volume_surge(self):
        closes = [100.0] * 50 + [102, 104, 106, 108, 110, 112, 114, 116, 118, 126]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertNotIn(("TRIM", "高潮頂"), rules(alerts))


class TimeStopTest(unittest.TestCase):
    def test_flat_position_after_20_days_warns(self):
        closes = [100.0] * 60
        bars = make_bars(closes)
        buy = bars.index[-25]
        alerts, _, _ = sell_rules.evaluate("X", 100, buy, bars, make_cfg())
        self.assertIn(("WARN", "時間止損"), rules(alerts))

    def test_recent_buy_no_time_stop(self):
        closes = [100.0] * 60
        bars = make_bars(closes)
        buy = bars.index[-5]
        alerts, _, _ = sell_rules.evaluate("X", 100, buy, bars, make_cfg())
        self.assertNotIn(("WARN", "時間止損"), rules(alerts))


class MoreTrendRulesTest(unittest.TestCase):
    def test_close_below_200ma_on_heavy_volume_sells(self):
        closes = [100.0] * 199 + [80.0]
        vols = [1_000_000] * 199 + [2_000_000]
        bars = make_bars(closes, vols=vols)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("SELL", "放量跌破200MA"), rules(alerts))

    def test_close_below_200ma_on_normal_volume_warns_only(self):
        closes = [100.0] * 199 + [80.0]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("WARN", "跌破200MA"), rules(alerts))
        self.assertNotIn(("SELL", "放量跌破200MA"), rules(alerts))

    def test_close_below_prior_10_day_low_warns(self):
        closes = [100.0] * 59 + [99.5]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("WARN", "跌破近10日低點"), rules(alerts))


class TrailingProfitLockTest(unittest.TestCase):
    def test_no_lock_alert_below_10_percent_peak(self):
        closes = [100.0] * 50 + [109.0, 100.5]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertNotIn("移動鎖利", {a.rule for a in alerts})

    def test_lock_trims_when_gain_falls_to_half_of_peak(self):
        # Peak 40% gain, so lock gain = 20%. Close at 119 is a 19% gain.
        closes = [100.0] * 50 + [140.0] * 3 + [119.0]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("TRIM", "移動鎖利"), rules(alerts))

    def test_lock_does_not_trim_above_lock_point(self):
        closes = [100.0] * 50 + [140.0] * 3 + [125.0]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertNotIn("移動鎖利", {a.rule for a in alerts})

    def test_lock_ratchets_up_with_new_peak(self):
        # Peak 50% gain moves lock to 25%. Close at 124 (24% gain) trims.
        closes = [100.0] * 50 + [140.0, 150.0, 124.0]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("TRIM", "移動鎖利"), rules(alerts))

    def test_drawdown_25_percent_trims_on_large_gain(self):
        # Peak gain 150%: lock 75% is at 175, but 25% drawdown from 250 is 187.5.
        # Close 185 is above the lock point and below the drawdown line.
        closes = [100.0] * 50 + [250.0, 185.0]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("TRIM", "最高點回撤"), rules(alerts))
        self.assertNotIn("移動鎖利", {a.rule for a in alerts})

    def test_drawdown_not_applied_at_or_below_20_percent_peak(self):
        # Peak 15% gain: lock 10% at 110 trims at close 86, but no drawdown trim.
        closes = [100.0] * 50 + [115.0, 86.0]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("TRIM", "移動鎖利"), rules(alerts))
        self.assertNotIn("最高點回撤", {a.rule for a in alerts})

    def test_old_giveback_sell_removed(self):
        # Peak 40%, close 119 would have triggered the removed SELL rule.
        closes = [100.0] * 50 + [140.0] * 3 + [119.0]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertNotIn("回吐獲利", {a.rule for a in alerts})

    def test_lock_arms_at_exact_10_percent_peak(self):
        # Float trap: 1.21 / 1.10 - 1 is just below 0.10. Close 1.10 is the lock point.
        closes = [1.10] * 50 + [1.21, 1.10]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 1.10, bars.index[0], bars, make_cfg())
        self.assertIn(("TRIM", "移動鎖利"), rules(alerts))

    def test_no_drawdown_trim_at_exact_20_percent_peak(self):
        # Float trap: 2.46 / 2.05 - 1 is just above 0.20. Peak is exactly 20%, so no drawdown trim.
        closes = [2.05] * 50 + [2.46, 1.80]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 2.05, bars.index[0], bars, make_cfg())
        self.assertNotIn("最高點回撤", {a.rule for a in alerts})

    def test_drawdown_trims_at_exact_25_percent(self):
        closes = [100.0] * 50 + [250.0, 187.5]
        bars = make_bars(closes)
        alerts, _, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertIn(("TRIM", "最高點回撤"), rules(alerts))


class InputTest(unittest.TestCase):
    def test_buy_date_after_data_raises(self):
        bars = make_bars([100.0] * 60)
        with self.assertRaises(ValueError):
            sell_rules.evaluate("X", 100, "2099-01-01", bars, make_cfg())

    def test_nan_last_close_raises(self):
        bars = make_bars([100.0] * 59 + [float("nan")])
        with self.assertRaises(ValueError):
            sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())

    def test_nan_last_volume_raises(self):
        vols = [1_000_000] * 59 + [float("nan")]
        bars = make_bars([100.0] * 60, vols=vols)
        with self.assertRaises(ValueError):
            sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())

    def test_empty_bars_raises_value_error(self):
        bars = make_bars([100.0] * 60).iloc[0:0]
        with self.assertRaises(ValueError):
            sell_rules.evaluate("X", 100, "2026-01-01", bars, make_cfg())

    def test_nan_mid_series_is_dropped_not_fatal(self):
        closes = [100.0] * 60
        closes[30] = float("nan")
        bars = make_bars(closes)
        alerts, stop, _ = sell_rules.evaluate("X", 100, bars.index[0], bars, make_cfg())
        self.assertAlmostEqual(stop, 90.0)


def load_monitor():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "positions-monitor.py")
    spec = importlib.util.spec_from_file_location("positions_monitor", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HoldingsParseTest(unittest.TestCase):
    def setUp(self):
        self.monitor = load_monitor()
        self.tmpdir = tempfile.mkdtemp()

    def write_csv(self, text):
        path = os.path.join(self.tmpdir, "holdings.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(text)
        return path

    def test_bad_rows_are_isolated(self):
        path = self.write_csv(
            "owner,symbol,market,shares,avg_cost,buy_date,initial_stop_pct\n"
            "L,2330.TW,TW,1000,850.5,2026-08-03,\n"
            "L,2317.TW,TW,,100,2026-08-03,\n"
            "B,AAPL,USA,10,210,2026-09-14,\n"
            "P,MSFT,US,10,nan,2026-09-14,\n"
        )
        holdings, errors = self.monitor.load_holdings(path)
        self.assertEqual([h["symbol"] for h in holdings], ["2330.TW"])
        self.assertEqual(len(errors), 3)

    def test_invalid_owner_is_row_error(self):
        path = self.write_csv(
            "owner,symbol,market,shares,avg_cost,buy_date,initial_stop_pct\n"
            "X,A.TW,TW,1,10,2026-08-03,\n"
            ",B.TW,TW,1,10,2026-08-03,\n"
        )
        holdings, errors = self.monitor.load_holdings(path)
        self.assertEqual(holdings, [])
        self.assertEqual(len(errors), 2)

    def test_invalid_stop_override_is_row_error(self):
        path = self.write_csv(
            "owner,symbol,market,shares,avg_cost,buy_date,initial_stop_pct\n"
            "L,A.TW,TW,1,10,2026-08-03,nan\n"
            "L,B.TW,TW,1,10,2026-08-03,-0.1\n"
            "L,C.TW,TW,1,10,2026-08-03,1.5\n"
            "L,D.TW,TW,1,10,,\n"
        )
        holdings, errors = self.monitor.load_holdings(path)
        self.assertEqual(holdings, [])
        self.assertEqual(len(errors), 4)

    def test_missing_required_column_raises_clear_error(self):
        path = self.write_csv("ticker,market,shares,avg_cost,buy_date\nAAPL,US,1,10,2026-09-14\n")
        with self.assertRaises(ValueError) as ctx:
            self.monitor.load_holdings(path)
        self.assertIn("symbol", str(ctx.exception))

    def test_optional_stop_override_blank_is_none(self):
        path = self.write_csv(
            "owner,symbol,market,shares,avg_cost,buy_date,initial_stop_pct\n"
            "B,AAPL,US,10,210,2026-09-14,0.08\n"
            "P,2330.TW,TW,1000,850.5,2026-08-03,\n"
        )
        holdings, _ = self.monitor.load_holdings(path)
        self.assertEqual(holdings[0]["initial_stop_pct"], 0.08)
        self.assertEqual(holdings[0]["owner"], "B")
        self.assertIsNone(holdings[1]["initial_stop_pct"])


class CleanBarsTest(unittest.TestCase):
    def test_incomplete_trailing_bar_is_dropped(self):
        monitor = load_monitor()
        bars = make_bars([100.0, 101.0, 102.0])
        bars.iloc[-1, bars.columns.get_loc("Open")] = float("nan")
        bars.iloc[-1, bars.columns.get_loc("Close")] = float("nan")
        cleaned = monitor.clean_bars(bars)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned["Close"].iloc[-1], 101.0)


if __name__ == "__main__":
    unittest.main()
