"""Payload fields a family never reads must not move its signals."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.strategy import IndicatorCache, Params, compute

POISON = {
    "htf_factor": 12,
    "htf_mode": "t3",
    "adx_min": 25.0,
    "adx_max": 40.0,
    "min_body_ratio": 0.4,
    "atr_pct_min": 0.3,
}


def _cache(n=900):
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 0.4, n))
    high = close + 0.35
    low = close - 0.35
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return IndicatorCache(high=high, low=low, close=close, open_=open_,
                          times=np.arange(n, dtype=np.int64) * 300, tf_seconds=300)


def _params(strategy: str, **overrides):
    return Params.from_config(SymbolConfig(symbol="X", strategy=strategy),
                              **overrides)


def test_a_family_that_reads_the_gates_does_move():
    cache = _cache()
    clean = compute(cache, _params("channel_break"))
    poisoned = compute(cache, _params("channel_break", **POISON))

    assert clean.buy.any() or clean.sell.any()
    assert not np.array_equal(clean.buy, poisoned.buy) or not np.array_equal(
        clean.sell, poisoned.sell)
