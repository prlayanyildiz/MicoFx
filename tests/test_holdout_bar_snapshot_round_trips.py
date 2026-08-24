"""Holdout bars round-trip on disk without an MT5 call."""
from __future__ import annotations

import numpy as np

from micofx.bar_snapshot import read, write
from micofx.mt5client import Bars


def _bars(n=8):
    rates = np.zeros(n, dtype=[
        ("time", np.int64), ("open", np.float64), ("high", np.float64),
        ("low", np.float64), ("close", np.float64), ("spread", np.float64),
        ("tick_volume", np.float64),
    ])
    rates["time"] = np.arange(n, dtype=np.int64) * 1800 + 1_787_000_000
    rates["open"] = 100.0
    rates["high"] = 101.0
    rates["low"] = 99.0
    rates["close"] = 100.5
    rates["spread"] = 2.0
    rates["tick_volume"] = 10.0
    return Bars(rates, int(rates["time"][-1] + 1800))


def test_a_snapshot_round_trips_the_holdout_window(tmp_path):
    bars = _bars()
    path = tmp_path / "GER40_M30.npz"
    write(path, symbol="GER40", timeframe="M30", bars=bars,
          info={"point": 0.1, "tick_value": 1.0, "tick_size": 0.1},
          min_stop=0.5)
    got = read(path)
    assert got["symbol"] == "GER40"
    assert got["timeframe"] == "M30"
    assert len(got["bars"]) == len(bars)
    assert got["bars"].last_closed_time == bars.last_closed_time
    assert got["bars"].forming_time == bars.forming_time
    np.testing.assert_array_equal(got["bars"].close, bars.close)
    np.testing.assert_array_equal(got["bars"].spread, bars.spread)
    assert got["info"]["point"] == 0.1
    assert got["min_stop"] == 0.5
