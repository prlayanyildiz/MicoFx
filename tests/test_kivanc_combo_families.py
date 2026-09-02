"""Kivanc combo piece that earned a first holdout: ichimoku.

AlphaTrend and MavilimW retired 26.08: alpha_trend could not clear
MIN_TEST_TRADES (7 vs 12, structural lag-2 cross); mavilim had enough
trades and lost (GER -20.2 R / PF 0.92). Their helpers must stay gone
(see test_retired_indicators_stay_gone).

Ichimoku is the TK cross against the cloud from 26 bars ago (no forward
displacement). BBW is not a family: atr_pct_min already gates dead
regimes. TD Sequential is a fade counter against an ATR-trail book.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import indicators as ind
from micofx.models import STRATEGIES
from micofx.strategy import _FAMILIES, IndicatorCache, Params, compute, opt_fields_read


def _series(n=400):
    rng = np.random.default_rng(11)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + 0.4
    low = close - 0.4
    return high, low, close


def test_ichimoku_cloud_does_not_read_future_bars():
    high, low, close = _series(500)
    tenkan, kijun, cloud_top, cloud_bot = ind.ichimoku_lines(high, low)
    ten2, kij2, top2, bot2 = ind.ichimoku_lines(high[:-12], low[:-12])
    assert np.allclose(tenkan[:-12], ten2)
    assert np.allclose(kijun[:-12], kij2)
    assert np.allclose(cloud_top[:-12], top2, equal_nan=True)
    assert np.allclose(cloud_bot[:-12], bot2, equal_nan=True)


def _cache_from(high, low, close):
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return IndicatorCache(high, low, close, times=np.arange(close.size) * 300,
                          tf_seconds=300, open_=open_, volume=np.ones(close.size))


def test_ichimoku_is_dispatched_and_never_both_sides():
    high, low, close = _series(600)
    sig = compute(_cache_from(high, low, close), Params(strategy="ichimoku"))
    assert "ichimoku" in STRATEGIES and "ichimoku" in _FAMILIES
    assert not np.any(sig.buy & sig.sell)
    assert sig.buy.size == close.size


def test_ichimoku_reads_htf_and_regime_gates():
    """02.09: ichimoku runs _trend_gate/_regime on purpose (not unread-flip)."""
    read = opt_fields_read("ichimoku")
    for field in ("htf_factor", "adx_min", "min_body_ratio", "atr_pct_min"):
        assert field in read
