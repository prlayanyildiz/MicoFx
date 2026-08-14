"""GER40's paper edge split, as a library, not a notebook.

On 14.08 the same holdout exits earned +0.153 R with real direction and
+0.048 R with a coin-flip. That split has to be re-runnable on every
config. Live trading does not read this module.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.edge_decomposition import decompose, replay


def test_fully_random_direction_has_no_direction_share():
    rng = np.random.default_rng(7)
    n = 200
    # Exit geometry pays +0.2 either way; direction is a coin-flip on top.
    base = np.full(n, 0.2)
    real = list(base + rng.choice([-0.3, 0.3], n))
    random_runs = [list(base + rng.choice([-0.3, 0.3], n)) for _ in range(20)]
    out = decompose(real, random_runs).as_dict()
    assert out["reason"] == ""
    assert out["n"] == n
    assert out["E"] is not None and out["E_random_mean"] is not None
    assert abs(out["direction_share"]) < 0.25


def test_perfect_direction_takes_the_whole_edge():
    n = 120
    real = [1.0] * n
    rng = np.random.default_rng(1)
    random_runs = []
    for _ in range(20):
        pick = rng.random(n) < 0.5
        random_runs.append([1.0 if p else -1.0 for p in pick])
    out = decompose(real, random_runs).as_dict()
    assert out["E"] == 1.0
    assert abs(out["E_random_mean"]) < 0.15
    assert out["direction_share"] is not None
    assert out["direction_share"] > 0.85
    assert out["E_random_p10"] is not None and out["E_random_p90"] is not None


def test_one_seed_does_not_invent_percentiles():
    real = [0.4] * 120
    out = decompose(real, [[-0.1] * 120]).as_dict()
    assert out["E_random_mean"] is not None
    assert out["E_random_p10"] is None and out["E_random_p90"] is None
    assert out["reason"] == "yetersiz tohum"


def test_thin_sample_produces_no_numbers():
    out = decompose([0.2] * 99, [[0.1] * 99] * 20).as_dict()
    assert out["n"] == 99
    assert out["E"] is None and out["WR"] is None and out["direction_share"] is None
    assert out["E_random_mean"] is None
    assert out["reason"] == "n<100, uretilmedi"


def test_replay_uses_simulate_and_respects_the_thin_bar():
    """A handful of bars cannot mint a split - simulate is the path, n is the gate."""
    from micofx.strategy import IndicatorCache, Params, Signals

    n = 80
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(np.full(n, 100.0), np.full(n, 100.0), close,
                           times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0)
    out = replay(cache, sig, open_, np.zeros(n), 0.01, p, seeds=20).as_dict()
    assert out["E"] is None
    assert out["reason"] == "n<100, uretilmedi"
