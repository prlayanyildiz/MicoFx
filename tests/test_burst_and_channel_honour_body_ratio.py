"""burst and channel_break must honour min_body_ratio like ichimoku/mtf_pullback."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.strategy import (
    IndicatorCache,
    Params,
    absent_regime_gates_to_zero,
    compute,
    opt_fields_read,
)


def _cache(n: int = 900) -> IndicatorCache:
    rng = np.random.default_rng(11)
    close = 100 + np.cumsum(rng.normal(0, 0.35, n))
    high = close + rng.uniform(0.05, 0.5, n)
    low = close - rng.uniform(0.05, 0.5, n)
    open_ = close + rng.normal(0, 0.02, n)
    return IndicatorCache(high, low, close, open_=open_, tf_seconds=1800)


def _params(strategy: str, **overrides):
    return Params.from_config(SymbolConfig(symbol="X", strategy=strategy), **overrides)


def test_burst_and_channel_read_min_body_ratio():
    assert "min_body_ratio" in opt_fields_read("burst")
    assert "min_body_ratio" in opt_fields_read("channel_break")


def test_absent_regime_gates_to_zero():
    stamped = {"adx_min": 0.0, "brst_range_z": 1.0}
    got = absent_regime_gates_to_zero("burst", stamped)
    assert got.get("adx_max") == 0
    assert got.get("min_body_ratio") == 0
    assert "adx_min" not in got


def test_min_body_ratio_filters_wick_heavy_bars():
    cache = _cache()
    for family in ("burst", "channel_break"):
        loose = compute(cache, _params(family, min_body_ratio=0.0))
        strict = compute(cache, _params(family, min_body_ratio=0.4))
        assert loose.buy.sum() + loose.sell.sum() >= strict.buy.sum() + strict.sell.sum()
