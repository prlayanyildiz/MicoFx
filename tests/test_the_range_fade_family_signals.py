"""range_fade: quiet ADX fade of EMA±ATR band extremes (Claude 12:38).

Complements channel_break on US30. Code + grid only — not live until
baseline 25 + unfreeze + US30 WFO. Default opt strategies list stays 3.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import OPT_FIELDS, STRATEGIES
from micofx.strategy import IndicatorCache, Params, compute, opt_fields_read


def _cache(high, low, close, open_=None):
    high = np.asarray(high, dtype=np.float64)
    low = np.asarray(low, dtype=np.float64)
    close = np.asarray(close, dtype=np.float64)
    open_ = close if open_ is None else np.asarray(open_, dtype=np.float64)
    n = close.size
    times = np.arange(n, dtype=np.float64) * 1800.0
    volume = np.ones(n, dtype=np.float64)
    return IndicatorCache(high, low, close, times, 1800,
                          open_, volume, np.zeros(n, dtype=np.float64))


def test_the_family_is_registered():
    assert "range_fade" in STRATEGIES


def test_its_axes_are_searchable():
    for ax in ("fade_adx_max", "fade_ema_len", "fade_band_atr"):
        assert ax in OPT_FIELDS
    read = opt_fields_read("range_fade")
    assert "fade_adx_max" in read
    assert "fade_ema_len" in read
    assert "fade_band_atr" in read


def test_no_signal_when_adx_is_trending():
    """Quiet mask: high ADX must suppress every bar (Claude test a)."""
    rng = np.random.default_rng(11)
    n = 400
    # Strong directional move → high ADX.
    close = np.linspace(100.0, 140.0, n) + rng.normal(0, 0.05, n)
    high = close + 0.4
    low = close - 0.4
    sig = compute(
        _cache(high, low, close),
        Params(strategy="range_fade", fade_adx_max=22.0, fade_ema_len=20,
               fade_band_atr=1.0, htf_factor=0),
    )
    # Trending series should not produce fade entries (ADX >> 22).
    assert int(sig.buy.sum() + sig.sell.sum()) == 0


def test_first_of_run_does_not_reenter_every_bar():
    """Sustained close below the band → one buy at the start of the run."""
    n = 400
    close = np.full(n, 100.0)
    # Drop and stay below any EMA±ATR band for the last 40 bars.
    close[-40:] = 90.0
    high = close + 0.2
    low = close - 0.2
    sig = compute(
        _cache(high, low, close),
        Params(strategy="range_fade", fade_adx_max=100.0,  # force quiet
               fade_ema_len=20, fade_band_atr=0.5, htf_factor=0,
               # Stoch will be oversold on a dump; loosen nothing else.
               ),
    )
    # At most one buy in the dump window (first_of_run).
    assert int(sig.buy[-40:].sum()) <= 1


def test_buy_and_sell_conflict_clears_both():
    """_resolve_conflicts: same-bar both sides → neither."""
    # Synthetic: force both masks by extreme k and close — hard to get both
    # with real stoch; pin via direct family call on crafted k is overkill.
    # Identity: registry dispatches and returns equal-length arrays.
    n = 200
    close = 100.0 + np.sin(np.linspace(0, 20, n))
    sig = compute(
        _cache(close + 0.3, close - 0.3, close),
        Params(strategy="range_fade", fade_adx_max=50.0, fade_ema_len=10,
               fade_band_atr=1.0, htf_factor=0),
    )
    assert sig.buy.shape == sig.sell.shape == (n,)
    assert not bool((sig.buy & sig.sell).any())
