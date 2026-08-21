"""MACD periods are independent grid axes; swapped values inverted the signal.

The shipped macd_flip grid never hits this (fast 6..16, slow 18..34). The
panel and POST /api/opt/params do: they range-check each period alone, so
macd_fast=26 / macd_slow=12 stores with HTTP 200. indicators.macd then
subtracted the shorter EMA from the longer one, and macd_flip's zero-cross
bought where classic MACD would sell.

Equal periods are the other degenerate: the line is identically zero.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import indicators as ind


def _close():
    return np.linspace(100.0, 110.0, 200) + np.sin(np.linspace(0, 8, 200))


def test_shipped_12_26_is_unchanged_by_the_swap():
    close = _close()
    # Recompute the old formula (no swap) against the helper after the clamp.
    line, sig, hist = ind.macd(close, 12, 26, 9)
    fast_ema = ind.ema(close, 12)
    slow_ema = ind.ema(close, 26)
    old_line = fast_ema - slow_ema
    old_sig = ind.ema(old_line, 9)
    old_hist = old_line - old_sig
    np.testing.assert_allclose(line, old_line)
    np.testing.assert_allclose(sig, old_sig)
    np.testing.assert_allclose(hist, old_hist)


def test_swapped_periods_match_the_classic_order():
    close = _close()
    classic = ind.macd(close, 12, 26, 9)
    swapped = ind.macd(close, 26, 12, 9)
    np.testing.assert_allclose(swapped[0], classic[0])
    np.testing.assert_allclose(swapped[1], classic[1])
    np.testing.assert_allclose(swapped[2], classic[2])


def test_swapped_histogram_is_not_the_negation_of_classic():
    """The bug: fast>slow produced -MACD, so zero-crosses flipped side."""
    close = _close()
    hist = ind.macd(close, 12, 26, 9)[2]
    inverted = ind.ema(close, 26) - ind.ema(close, 12)
    inverted_hist = inverted - ind.ema(inverted, 9)
    got = ind.macd(close, 26, 12, 9)[2]
    assert not np.allclose(got, inverted_hist)
    np.testing.assert_allclose(got, hist)


def test_equal_periods_do_not_collapse_the_line_to_zero():
    close = _close()
    line, _sig, hist = ind.macd(close, 12, 12, 9)
    assert np.any(np.abs(line) > 1e-12)
    assert np.any(np.abs(hist) > 1e-12)


def test_macd_periods_is_the_single_order_source():
    assert ind.macd_periods(12, 26) == (12, 26)
    assert ind.macd_periods(26, 12) == (12, 26)
    assert ind.macd_periods(12, 12) == (12, 13)
    assert ind.macd_periods(0, 5) == (1, 5)


def test_warmup_and_required_bars_use_the_ordered_slow():
    """After the swap, raw macd_slow can be the short period. Warmup and
    required_bars used to size from that raw field and under-warm 8 inverted
    grid cells by 1-4 bars. Same helper as macd() itself closes that gap.
    atr_period=1 so ATR does not mask the MACD term.
    """
    from micofx.strategy import IndicatorCache, Params, compute, required_bars

    close = _close()
    high = close + 0.4
    low = close - 0.4
    cache = IndicatorCache(high, low, close)
    classic = Params(strategy="macd_flip", macd_fast=12, macd_slow=34,
                     macd_signal=9, atr_period=1)
    swapped = Params(strategy="macd_flip", macd_fast=34, macd_slow=12,
                     macd_signal=9, atr_period=1)
    assert required_bars(classic) == required_bars(swapped)
    left = compute(cache, classic)
    right = compute(cache, swapped)
    np.testing.assert_array_equal(left.buy, right.buy)
    np.testing.assert_array_equal(left.sell, right.sell)


def test_swapped_and_classic_share_one_cache_key():
    from micofx.strategy import IndicatorCache

    close = _close()
    cache = IndicatorCache(close + 0.4, close - 0.4, close)
    cache.macd(12, 26, 9)
    cache.macd(26, 12, 9)
    assert list(cache._macd) == [(12, 26, 9)]
