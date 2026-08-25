"""Kivanc combo pieces that are not already a live family.

AlphaTrend (RSI mode) is a trailing ATR line gated by RSI>=50, not SuperTrend.
MavilimW is nested WMAs; the slope flip is the signal.
Ichimoku is the TK cross against the cloud that was computed 26 bars ago
(no forward displacement).

BBW is not a family: ``atr_pct_min`` is the existing horizontal/dead-regime
gate. TD Sequential is a fade counter and does not fit the trail-only exit.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

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


def test_alpha_trend_prefix_matches_the_full_series():
    high, low, close = _series()
    full = ind.alpha_trend_rsi(high, low, close, period=14, coeff=1.0)
    head = ind.alpha_trend_rsi(high[:-8], low[:-8], close[:-8], period=14, coeff=1.0)
    assert np.allclose(full[:-8], head)


def test_alpha_trend_does_not_drop_while_rsi_is_high():
    n = 80
    close = np.linspace(100.0, 120.0, n)
    high = close + 0.3
    low = close - 0.3
    line = ind.alpha_trend_rsi(high, low, close, period=14, coeff=1.0)
    # After warmup a rising tape should not let the RSI-bullish branch fall.
    assert np.all(np.diff(line[30:]) >= -1e-12)


def test_mavilim_is_causal():
    high, low, close = _series()
    full = ind.mavilim_w(close, 3, 5)
    head = ind.mavilim_w(close[:-8], 3, 5)
    assert np.allclose(full[:-8], head)


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


@pytest.mark.parametrize("name", ("alpha_trend", "mavilim", "ichimoku"))
def test_family_is_dispatched_and_never_both_sides(name):
    high, low, close = _series(600)
    sig = compute(_cache_from(high, low, close), Params(strategy=name))
    assert name in STRATEGIES and name in _FAMILIES
    assert not np.any(sig.buy & sig.sell)
    assert sig.buy.size == close.size


def test_alpha_trend_reads_rsi_length_only_among_poison():
    read = opt_fields_read("alpha_trend")
    assert "rsi_length" in read
    for field in ("htf_factor", "adx_min", "min_body_ratio", "atr_pct_min",
                  "st_mult", "t3_length"):
        assert field not in read


def test_mavilim_and_ichimoku_are_unread_flip_shaped():
    for name in ("mavilim", "ichimoku"):
        read = opt_fields_read(name)
        for field in ("htf_factor", "adx_min", "min_body_ratio", "atr_pct_min"):
            assert field not in read
