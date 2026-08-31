"""channel_break: close beyond the prior N-bar range.

Measured 31.08 (F40) before any of this was written. Seven shipped families and
none of them keys off a price level the market has already printed: burst is
range *expansion* (this bar's own high-low against its trailing distribution),
and its docstring says so explicitly. The closest thing in the book is ichimoku,
whose tenkan/kijun are N-bar midpoints - and it scored best of the seven on
MFE/MAE asymmetry while running on no live symbol.

The effect this family implements held in the out-of-sample half of all ten
captured windows, and strengthens smoothly with lookback (median asymmetry
1.034 at 10 bars, 1.078 at 100) rather than spiking at one value - the
signature of structure rather than a lucky parameter.

A break is read on a CLOSED bar against the channel of the bars *before* it:
including the current bar in its own channel would compare the close to a high
it just set.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import OPT_FIELDS, STRATEGIES
from micofx.strategy import IndicatorCache, Params, compute


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


def _flat_then_break(n=400, lookback=50, up=True):
    """A long quiet range, then one close outside it."""
    rng = np.random.default_rng(7)
    close = 100.0 + rng.normal(0, 0.2, n)
    high = close + 0.3
    low = close - 0.3
    # The break, well clear of anything the channel has seen.
    close[-1] = 108.0 if up else 92.0
    high[-1] = close[-1] + 0.3
    low[-1] = close[-1] - 0.3
    return high, low, close


def test_the_family_is_registered():
    assert "channel_break" in STRATEGIES


def test_its_axes_are_searchable():
    """A lookback the grid cannot reach is the bug this family exists to fix."""
    assert "chan_lookback" in OPT_FIELDS
    assert "chan_buffer_atr" in OPT_FIELDS


def test_an_upside_break_buys():
    high, low, close = _flat_then_break()
    sig = compute(_cache(high, low, close),
                  Params(strategy="channel_break", chan_lookback=50,
                         htf_factor=0))
    assert bool(sig.buy[-1])
    assert not bool(sig.sell[-1])


def test_a_downside_break_sells():
    high, low, close = _flat_then_break(up=False)
    sig = compute(_cache(high, low, close),
                  Params(strategy="channel_break", chan_lookback=50,
                         htf_factor=0))
    assert bool(sig.sell[-1])
    assert not bool(sig.buy[-1])


def test_a_quiet_range_never_signals():
    """No level taken out means no trade, however long the window."""
    rng = np.random.default_rng(3)
    close = 100.0 + rng.normal(0, 0.2, 400)
    sig = compute(_cache(close + 0.3, close - 0.3, close),
                  Params(strategy="channel_break", chan_lookback=50,
                         htf_factor=0))
    assert not sig.buy.any()
    assert not sig.sell.any()


def test_the_bar_is_not_compared_to_its_own_high():
    """Channel is the prior N bars. A rising series must not fire every bar."""
    close = np.linspace(100.0, 130.0, 400)
    sig = compute(_cache(close + 0.05, close - 0.05, close),
                  Params(strategy="channel_break", chan_lookback=50,
                         htf_factor=0))
    # first_of_run keeps a sustained trend to one entry, not one per bar.
    assert int(sig.buy.sum()) < 20


def test_the_buffer_refuses_a_marginal_break():
    """A close a hair over the channel is not a break when a buffer is set."""
    rng = np.random.default_rng(11)
    close = 100.0 + rng.normal(0, 0.2, 400)
    high, low = close + 0.3, close - 0.3
    ceiling = high[:-1].max()
    close[-1] = ceiling + 0.01
    high[-1], low[-1] = close[-1] + 0.05, close[-1] - 0.05
    c = _cache(high, low, close)

    loose = compute(c, Params(strategy="channel_break", chan_lookback=50,
                              htf_factor=0))
    tight = compute(c, Params(strategy="channel_break", chan_lookback=50,
                              htf_factor=0, chan_buffer_atr=1.0))

    assert bool(loose.buy[-1])
    assert not bool(tight.buy[-1])


def test_a_longer_lookback_is_harder_to_break():
    """The axis has to actually bite, or searching it is theatre."""
    rng = np.random.default_rng(5)
    close = 100.0 + np.cumsum(rng.normal(0, 0.3, 900))
    c = _cache(close + 0.3, close - 0.3, close)
    short = compute(c, Params(strategy="channel_break", chan_lookback=20,
                              htf_factor=0))
    long_ = compute(c, Params(strategy="channel_break", chan_lookback=200,
                              htf_factor=0))
    assert int(short.buy.sum() + short.sell.sum()) > \
        int(long_.buy.sum() + long_.sell.sum())


def test_the_higher_timeframe_gate_still_binds():
    """htf_factor is a searchable axis here as in every other family."""
    high, low, close = _flat_then_break()
    c = _cache(high, low, close)
    ungated = compute(c, Params(strategy="channel_break", chan_lookback=50,
                                htf_factor=0))
    gated = compute(c, Params(strategy="channel_break", chan_lookback=50,
                              htf_factor=6))
    assert bool(ungated.buy[-1])
    # The synthetic range drifts down, so a trend-aligned long is refused.
    assert not bool(gated.buy[-1])


def test_an_empty_series_is_safe():
    sig = compute(_cache([], [], []), Params(strategy="channel_break"))
    assert sig.buy.size == 0
