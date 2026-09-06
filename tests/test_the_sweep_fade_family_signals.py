"""sweep_fade: failed sweep of prior N-bar extreme while ADX capped (Claude 13:16).

Preferred 4th family over range_fade (book-wide). Code + grid only — not
live until baseline 25 + unfreeze + WFO. Default opt strategies stay 3.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import OPT_FIELDS, STRATEGIES
from micofx.strategy import (
    MIN_PULL_DEPTH_ATR,
    IndicatorCache,
    Params,
    compute,
    opt_fields_read,
    searchable_axes,
)


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
    assert "sweep_fade" in STRATEGIES


def test_its_axes_are_searchable():
    for ax in ("sweep_lookback", "sweep_pierce_atr", "sweep_close_pct", "adx_max"):
        assert ax in OPT_FIELDS or ax == "adx_max"
    read = opt_fields_read("sweep_fade")
    assert "sweep_lookback" in read
    assert "adx_max" in read  # revives the dead axis


def test_no_signal_when_adx_above_cap():
    """Quiet mask: trending ADX must suppress (Claude test a)."""
    rng = np.random.default_rng(21)
    n = 400
    close = np.linspace(100.0, 140.0, n) + rng.normal(0, 0.05, n)
    high = close + 0.5
    low = close - 0.5
    # Spike a fake sweep wick that would otherwise qualify.
    low[-1] = close[-1] - 5.0
    high[-1] = close[-1] + 0.2
    open_ = close.copy()
    open_[-1] = close[-1] - 0.1
    close[-1] = close[-1] + 0.05  # green close back "inside"
    sig = compute(
        _cache(high, low, close, open_),
        Params(strategy="sweep_fade", adx_max=15.0, sweep_lookback=20,
               sweep_pierce_atr=0.0, sweep_close_pct=0.5, htf_factor=0),
    )
    assert int(sig.buy.sum() + sig.sell.sum()) == 0


def test_first_of_run_on_repeated_sweeps():
    n = 400
    close = np.full(n, 100.0)
    high = close + 0.3
    low = close - 0.3
    open_ = close.copy()
    # Repeated downside sweeps with reclaim closes.
    for i in range(n - 30, n):
        low[i] = 95.0
        close[i] = 100.5
        open_[i] = 99.5
        high[i] = 100.8
    sig = compute(
        _cache(high, low, close, open_),
        Params(strategy="sweep_fade", adx_max=0.0,  # quiet off
               sweep_lookback=15, sweep_pierce_atr=0.0,
               sweep_close_pct=0.5, htf_factor=0),
    )
    assert int(sig.buy[-30:].sum()) <= 1
    assert not bool((sig.buy & sig.sell).any())


def test_required_bars_includes_sweep_lookback():
    from micofx.strategy import required_bars

    p = Params(strategy="sweep_fade", sweep_lookback=40, htf_factor=0)
    assert required_bars(p) >= 42


def test_pull_depth_grid_drops_values_below_floor():
    """Claude 13:16: 0.3 clamps to 0.5 — searchable_axes must dedupe."""
    cleaned = searchable_axes(
        "mtf_pullback",
        {"pull_depth_atr": [0.3, 0.5, 0.8, 1.2]},
    )
    assert 0.3 not in cleaned["pull_depth_atr"]
    assert cleaned["pull_depth_atr"][0] >= MIN_PULL_DEPTH_ATR
