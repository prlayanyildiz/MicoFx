"""Holdout bars round-trip on disk without an MT5 call."""
from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from micofx.bar_snapshot import read, write
from micofx.bars import Bars
from micofx.models import SymbolConfig


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


def _pin():
    return {
        "segments": 5, "trade_all_hours": False, "day_end_flatten_min": 0,
        "charge_costs": True, "max_cost_pct_of_risk": 18.0,
        "config": SymbolConfig(symbol="GER40", timeframe="M30").to_dict(),
    }


def test_a_snapshot_round_trips_the_holdout_window(tmp_path):
    bars = _bars()
    path = tmp_path / "GER40_M30.npz"
    write(path, symbol="GER40", timeframe="M30", bars=bars,
          info={"point": 0.1, "tick_value": 1.0, "tick_size": 0.1},
          min_stop=0.5, spread_scale=3.35, spread_scale_n=277_649, **_pin())
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
    assert got["spread_scale"] == 3.35
    assert got["spread_scale_n"] == 277_649
    assert got["segments"] == 5
    assert got["charge_costs"] is True
    assert got["max_cost_pct_of_risk"] == 18.0
    assert got["config"]["symbol"] == "GER40"


def test_a_thin_histogram_is_refused_not_stored_as_one(tmp_path):
    """Replay must not inherit _spread_scale's silent 1.0 on failure."""
    with pytest.raises(ValueError, match="spread_scale_n"):
        write(tmp_path / "x.npz", symbol="GER40", timeframe="M30", bars=_bars(),
              info={"point": 0.1, "tick_value": 1.0, "tick_size": 0.1},
              min_stop=0.5, spread_scale=1.0, spread_scale_n=0, **_pin())
    write(tmp_path / "ok.npz", symbol="GER40", timeframe="M30", bars=_bars(),
          info={"point": 0.1, "tick_value": 1.0, "tick_size": 0.1},
          min_stop=0.5, spread_scale=1.0, spread_scale_n=400, **_pin())


def test_a_cost_free_snapshot_is_refused(tmp_path):
    pin = _pin()
    pin["charge_costs"] = False
    with pytest.raises(ValueError, match="charge_costs"):
        write(tmp_path / "x.npz", symbol="GER40", timeframe="M30", bars=_bars(),
              info={"point": 0.1, "tick_value": 1.0, "tick_size": 0.1},
              min_stop=0.5, spread_scale=3.35, spread_scale_n=400, **pin)


def test_importing_the_snapshot_does_not_load_metatrader5():
    """Replay process must not import the MT5 binding. Isolated so other
    tests that already imported engine cannot poison sys.modules."""
    script = (
        "import sys\n"
        "assert 'MetaTrader5' not in sys.modules\n"
        "import micofx.bar_snapshot\n"
        "loaded = [k for k in sys.modules if k == 'MetaTrader5' "
        "or k.startswith('MetaTrader5.') or k == 'micofx.engine' "
        "or k == 'micofx.mt5client']\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_pinned_floor_matches_the_live_histogram_floor():
    from micofx.bar_snapshot import SPREAD_RATIO_MIN_SAMPLES as snap
    from micofx.engine import SPREAD_RATIO_MIN_SAMPLES as live
    assert snap == live == 400
