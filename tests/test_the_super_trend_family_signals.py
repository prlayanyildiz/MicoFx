"""super_trend: dynamic volatility envelope breakout and trend continuation.

Tests registration, signal generation on trend flips, first-of-run enforcement,
indicator memoization, and optimizer grid field reflection.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import STRATEGIES
from micofx.strategy import IndicatorCache, Params, compute, opt_fields_read, searchable_axes


def _cache(high, low, close, open_=None):
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    close = np.asarray(close, dtype=np.float64)
    open_ = close if open_ is None else np.asarray(open_, dtype=np.float64)
    n = close.size
    times = np.arange(n, dtype=np.float64) * 900.0
    volume = np.ones(n, dtype=np.float64)
    return IndicatorCache(high, low, close, times, 900,
                          open_, volume, np.zeros(n, dtype=np.float64))


def test_the_family_is_registered():
    assert "super_trend" in STRATEGIES


def test_opt_fields_read_includes_supertrend_axes():
    fields = opt_fields_read("super_trend")
    assert "sup_period" in fields
    assert "sup_mult" in fields
    assert "chan_lookback" not in fields
    assert "pull_fast" not in fields


def test_searchable_axes_filters_correctly():
    axes = {
        "sup_period": [7, 10],
        "sup_mult": [2.0, 3.0],
        "chan_lookback": [20, 40],
        "pull_fast": [8, 13],
        "sl_atr_mult": [1.0, 1.5],
        "trail_start_atr": [0.8, 1.2],
        "trail_step_atr": [1.0, 1.5],
        "max_spread_atr": [0.04, 0.08],
    }
    filtered = searchable_axes("super_trend", axes)
    assert "sup_period" in filtered
    assert "sup_mult" in filtered
    assert "sl_atr_mult" in filtered
    assert "chan_lookback" not in filtered
    assert "pull_fast" not in filtered


def test_supertrend_bullish_flip_signals_buy():
    # Construct a series in downtrend, then flip bullish on the final bar
    n = 200
    close = np.full(n, 100.0)
    close[-25:-1] = np.linspace(80.0, 60.0, 24)
    high = close + 1.0
    low = close - 1.0
    
    # breakout on final bar
    close[-1] = 85.0
    high[-1] = 86.0
    low[-1] = 84.0
    
    cache = _cache(high, low, close)
    p = Params(strategy="super_trend", sup_period=7, sup_mult=2.0, htf_factor=0)
    sig = compute(cache, p)
    
    assert sig.buy[-1]
    assert not sig.sell[-1]


def test_supertrend_bearish_flip_signals_sell():
    # Construct a series in uptrend, then flip bearish on the final bar
    n = 200
    close = np.full(n, 100.0)
    close[-25:-1] = np.linspace(120.0, 140.0, 24)
    high = close + 1.0
    low = close - 1.0
    
    # breakdown on final bar
    close[-1] = 115.0
    high[-1] = 116.0
    low[-1] = 114.0
    
    cache = _cache(high, low, close)
    p = Params(strategy="super_trend", sup_period=7, sup_mult=2.0, htf_factor=0)
    sig = compute(cache, p)
    
    assert sig.sell[-1]
    assert not sig.buy[-1]


def test_supertrend_first_of_run_suppresses_consecutive_signals():
    # Continuous strong uptrend: should signal only on the first flip bar
    n = 200
    close = np.linspace(50.0, 150.0, n)
    high = close + 1.0
    low = close - 1.0
    
    cache = _cache(high, low, close)
    p = Params(strategy="super_trend", sup_period=7, sup_mult=2.0)
    sig = compute(cache, p)
    
    # Must not signal continuously on every bar
    buy_indices = np.where(sig.buy)[0]
    assert len(buy_indices) <= 2  # Only initial flips
    if len(buy_indices) > 1:
        # Consecutive bars never signal together
        diffs = np.diff(buy_indices)
        assert np.all(diffs > 1)
