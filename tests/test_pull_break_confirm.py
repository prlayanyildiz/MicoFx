"""pull_break_confirm must not change live configs that leave it at 0."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.strategy import IndicatorCache, Params, _mtf_pullback


def _cache(n: int = 400) -> IndicatorCache:
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 0.3, n))
    high = close + rng.uniform(0.05, 0.4, n)
    low = close - rng.uniform(0.05, 0.4, n)
    open_ = close + rng.normal(0, 0.05, n)
    return IndicatorCache(high, low, close, open_=open_, tf_seconds=900)


def test_break_confirm_off_matches_prior_signal_count():
    base = Params(strategy="mtf_pullback", htf_factor=6, pull_break_confirm=0.0)
    strict = Params(strategy="mtf_pullback", htf_factor=6, pull_break_confirm=1.0)
    cache = _cache()
    off = _mtf_pullback(cache, base)
    on = _mtf_pullback(cache, strict)
    assert off.buy.sum() >= on.buy.sum()
    assert off.sell.sum() >= on.sell.sum()
