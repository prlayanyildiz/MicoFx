"""A 0.3 ATR 'pullback' is noise, not a setup.

NAS100 live (GAP-5, mtf_pullback/M30, pull_depth_atr=0.3, sl=1.0) printed
+60 R on fill-next-open paper and -11 R / 22 SL of 34 live. Several SL
deaths lasted 20 minutes with MFE < 0.6 R: the 'dip' was inside the same
M30 bar's noise, then the 1.0 ATR hard stop ate the ticket before the
trail (start 1.0) could arm.

The shipped grid offered 0.3. Compute must treat anything shallower than
the dataclass default (0.5) as 0.5 so a search that still emits 0.3 cannot
trade noise, and the grid must stop offering it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.strategy import IndicatorCache, Params, compute

N = 900
ROOT = Path(__file__).resolve().parents[1]


def _cache(seed: int = 2, tf: int = 1800) -> IndicatorCache:
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 1.0, N) + np.linspace(-0.35, 0.35, N)
    close = 20000.0 + np.cumsum(steps) * 8.0
    open_ = np.concatenate(([close[0]], close[:-1]))
    span = np.abs(rng.normal(0.0, 1.0, N)) * 6.0 + 1.0
    high = np.maximum(open_, close) + span
    low = np.minimum(open_, close) - span
    times = 1_786_000_000 + np.arange(N, dtype=np.int64) * tf
    return IndicatorCache(
        high, low, close, times, tf, open_,
        rng.integers(50, 5000, N).astype(np.float64), np.full(N, 1.2),
    )


def _sig(depth: float, cache: IndicatorCache):
    return compute(cache, Params(
        strategy="mtf_pullback", pull_depth_atr=depth,
        pull_fast=21, htf_factor=3, t3_length=4, pull_max_bars=4,
    ))


def test_a_sub_half_atr_depth_is_the_same_series_as_half():
    """Seed 2 currently fires one extra 0.3-ATR dip that 0.5 refuses."""
    cache = _cache(2)
    shallow = _sig(0.3, cache)
    floor = _sig(0.5, cache)
    assert (shallow.buy == floor.buy).all()
    assert (shallow.sell == floor.sell).all()
    assert int(floor.buy.sum() + floor.sell.sum()) > 0


def test_a_deeper_depth_is_still_allowed_to_be_stricter():
    cache = _cache(2)
    mid = _sig(0.5, cache)
    deep = _sig(1.2, cache)
    assert (deep.buy <= mid.buy).all()
    assert (deep.sell <= mid.sell).all()
    assert int(deep.buy.sum() + deep.sell.sum()) < int(mid.buy.sum() + mid.sell.sum())


def test_the_shipped_grid_no_longer_offers_noise_depth():
    blob = json.loads((ROOT / "config" / "defaults.json").read_text(encoding="utf-8"))
    depths = blob["optimizer"]["strategy_grids"]["mtf_pullback"]["pull_depth_atr"]
    assert min(depths) >= 0.5
    assert 0.3 not in depths
