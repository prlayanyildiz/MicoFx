"""The simulator traded gap fills the live engine has always refused.

Live has a stale-signal gate: a closed bar's signal dies two timeframes after
that bar closes (``signal_bar_expired``, ``entry_block = "bar_bosluk"``). It
exists because Friday's last M30 close arriving at Monday's open is not a
signal any more - 24.08 GER40 took exactly that fill and lost 1 R in twelve
minutes.

``simulate`` had no equivalent. It fills every signal at ``j0 = i + 1`` no
matter how much wall-clock sits between bar ``i`` and bar ``i + 1``. Bar
arrays from MT5 are dense - Friday 22:45 is followed directly by Monday 03:15
- so every weekend and every overnight session gap was a fill the search
counted and the live bot would refuse.

That is not a cost-accounting difference. It is the search scoring trades on
a population live cannot trade, and the flip families are hit hardest: a flip
is a single transition bar, and the last bar before a session close is an
ordinary signal bar.

``session_mask``/``tradable`` does not cover this - it masks whether the fill
*bar* is inside a trading window, and Monday's open very much is.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from micofx import backtest as bt
from micofx.sessions import MAX_SIGNAL_BAR_AGE_BARS
from micofx.strategy import IndicatorCache, Params

M30 = 1800
START = 1_700_000_000


def _series(gap_at: int | None, gap_sec: int, n: int = 400):
    """Rising ramp; optionally a calendar hole after bar ``gap_at``."""
    times = np.arange(n, dtype=np.int64) * M30 + START
    if gap_at is not None:
        times[gap_at + 1:] += gap_sec - M30
    close = np.linspace(100.0, 140.0, n)
    open_ = np.empty_like(close)
    open_[0] = close[0]
    open_[1:] = close[:-1]
    high = np.maximum(open_, close) + 0.5
    low = np.minimum(open_, close) - 0.5
    return times, open_, high, low, close


def _run(gap_at, gap_sec, entry_bar):
    n = 400
    times, open_, high, low, close = _series(gap_at, gap_sec, n)
    spread = np.full(n, 2.0)
    cost = spread * 0.01
    cache = IndicatorCache(high, low, close, times, M30, open_,
                           np.full(n, 100.0), cost)
    p = Params(strategy="t3_flip")
    p.sl_atr_mult = 2.0
    # One hand-placed signal on ``entry_bar`` so the test measures the gate,
    # not a family's opinion about a synthetic ramp.
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    buy[entry_bar] = True
    sig = _Sig(buy, sell, cache)
    entries = np.array([entry_bar], dtype=np.int64)
    return bt.simulate(cache, sig, open_, spread, 0.01, p,
                       entries=entries, spread_price=cost,
                       lo=0, hi=n)


class _Sig:
    def __init__(self, buy, sell, cache):
        self.buy, self.sell = buy, sell
        self.atr = np.full(buy.size, 1.0)
        self.cache = cache


# ------------------------------------------------------------- the defect

def test_a_weekend_gap_fill_is_not_counted():
    """Friday's last bar, Monday's open. 52 hours, not one M30."""
    res = _run(gap_at=200, gap_sec=52 * 3600, entry_bar=200)
    assert res.trades == 0


def test_an_overnight_session_gap_fill_is_not_counted():
    """GER40 closes 22:59 and reopens 03:15 - a four-hour hole every day."""
    res = _run(gap_at=200, gap_sec=4 * 3600, entry_bar=200)
    assert res.trades == 0


def test_the_boundary_matches_the_live_gate():
    """Live keeps the signal for MAX_SIGNAL_BAR_AGE_BARS after the close."""
    live = (1 + MAX_SIGNAL_BAR_AGE_BARS) * M30
    assert _run(gap_at=200, gap_sec=live, entry_bar=200).trades == 1
    assert _run(gap_at=200, gap_sec=live + M30, entry_bar=200).trades == 0


# --------------------------------------------------- what must keep working

def test_a_continuous_series_still_fills():
    assert _run(gap_at=None, gap_sec=0, entry_bar=200).trades == 1


def test_a_gap_elsewhere_does_not_block_an_unrelated_signal():
    """The hole is after bar 200; a signal at 250 fills at 251 as normal."""
    assert _run(gap_at=200, gap_sec=52 * 3600, entry_bar=250).trades == 1


def test_a_signal_on_the_bar_after_the_gap_still_fills():
    """Monday's first bar is a perfectly good signal bar."""
    assert _run(gap_at=200, gap_sec=52 * 3600, entry_bar=201).trades == 1
