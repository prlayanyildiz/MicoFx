"""Family sweeps on the same TF must not pickle thirteen copies of the bars.

A 6-symbol x 13-family x 3-TF search submitted ~234 jobs, each carrying its
own copy of the window. Thirteen M15 workers on GER40 pickled the same 8000
bars. One npy folder per (symbol, TF), mmap in the worker, is the same
arrays without the serialize cost.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_plan_symbol_reads_shared_from_variant import (
    OPERATOR_SL,
    _Bars,
    _opt,
)

from micofx.models import SymbolConfig
from micofx.optimizer import (
    _sweep_worker,
    load_sweep_bars,
    write_sweep_bars,
)


def test_write_and_load_round_trip(tmp_path):
    bars = _Bars(n=64)
    dest = tmp_path / "GER40_M15"
    write_sweep_bars(dest, bars)
    got = load_sweep_bars(dest)
    np.testing.assert_array_equal(got["close"], bars.close)
    np.testing.assert_array_equal(got["time"], bars.time)


def test_same_tf_jobs_share_one_bars_path():
    shared = {"sl_atr_mult": list(OPERATOR_SL), "trail_start_atr": [0.5],
              "trail_step_atr": [1.0]}
    variants = [
        {"key": name, "strategy": name, "own": {}, "grid": dict(shared),
         "shared": shared}
        for name in ("t3_stoch", "stoch_flip")
    ]
    opt = _opt()
    try:
        plan = opt._plan_symbol(
            SymbolConfig(symbol="GER40", magic=1),
            lookback_days=30, bar_cap=2000, variants=variants,
            min_trades=10, segments=3, max_combos=20, min_positive=0.5,
            plateau=0.2, timeframes=["M30"], refine_rounds=0,
        )
        jobs = plan["jobs"]
        assert len(jobs) == 2
        paths = {j["bars_path"] for j in jobs}
        assert len(paths) == 1
        assert all("bars" not in j for j in jobs)
        loaded = load_sweep_bars(Path(jobs[0]["bars_path"]))
        np.testing.assert_array_equal(loaded["close"], _Bars().close)
    finally:
        opt._clear_sweep_bars()


def test_the_worker_loads_bars_from_the_path():
    src = inspect.getsource(_sweep_worker)
    assert "load_sweep_bars" in src
    assert 'payload["bars"]' not in src
