"""File-only cost/R share: no client, no live histogram, no rescored net R."""
from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

from micofx.bar_snapshot import read, write
from micofx.bars import Bars
from micofx.holdout_cost import cost_share, replay
from micofx.models import SymbolConfig


def test_share_counts_trades_above_the_live_gate_without_rescoring():
    costs = [0.10, 0.18, 0.20, 0.40]
    rs = [1.0, -1.0, 0.5, -0.5]
    got = cost_share(costs, rs, 18.0)
    assert got["n"] == 4
    assert got["n_above"] == 2
    assert got["share_above"] == 0.5
    assert got["wins_above"] == 1
    assert got["losses_above"] == 1
    assert got["median"] == pytest.approx(0.19)
    assert "net_r" not in got


def test_empty_window_is_insufficient_not_a_zero_share():
    got = cost_share([], [], 18.0)
    assert got["n"] == 0
    assert got["share_above"] is None


def test_importing_the_replay_does_not_load_metatrader5():
    script = (
        "import sys\n"
        "assert 'MetaTrader5' not in sys.modules\n"
        "import micofx.holdout_cost\n"
        "loaded = [k for k in sys.modules if k == 'MetaTrader5' "
        "or k.startswith('MetaTrader5.') or k == 'micofx.engine' "
        "or k == 'micofx.mt5client']\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def _window(n=900):
    rates = np.zeros(n, dtype=[
        ("time", np.int64), ("open", np.float64), ("high", np.float64),
        ("low", np.float64), ("close", np.float64), ("spread", np.float64),
        ("tick_volume", np.float64),
    ])
    rates["time"] = np.arange(n, dtype=np.int64) * 1800 + 1_700_000_000
    rates["open"] = 100.0
    rates["high"] = 101.0
    rates["low"] = 99.0
    rates["close"] = 100.5
    rates["spread"] = 2.0
    rates["tick_volume"] = 10.0
    return Bars(rates, int(rates["time"][-1] + 1800))


def test_replay_reads_the_pin_and_does_not_need_a_client(tmp_path):
    path = tmp_path / "GER40_M30.npz"
    cfg = SymbolConfig(symbol="GER40", timeframe="M30", strategy="stoch_flip")
    write(path, symbol="GER40", timeframe="M30", bars=_window(),
          info={"point": 0.1, "tick_value": 1.0, "tick_size": 0.1},
          min_stop=0.5, spread_scale=3.35, spread_scale_n=400,
          segments=5, trade_all_hours=False, day_end_flatten_min=0,
          charge_costs=True, max_cost_pct_of_risk=18.0, config=cfg.to_dict())
    got = replay(read(path))
    assert got["symbol"] == "GER40"
    assert got["spread_scale"] == 3.35
    assert got["threshold_pct"] == 18.0
    assert "net_r" not in got
    assert got["lo"] < got["hi"]
