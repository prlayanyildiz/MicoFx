"""max_open>1 must allow overlapping fills the sequential loop forbids.

Found in 417 book-magic deals: the 3rd concurrent slot on the same symbol
was −4.99$ / 23.8% (n=21). simulate walked one position at a time, so a
max_positions cap could not be scored on the same holdout as skip-after-loss.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def _run(max_open: int):
    n = 80
    high = np.full(n, 100.0)
    # Stay above a 1-ATR stop (sl=99) so the first fill is still open at bar 20.
    low = np.full(n, 99.2)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    # Two buys before the first stop: fill 11 and 21, both die at bar 40.
    low[40] = 90.0
    close[40] = 95.0
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    buy[20] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0, cooldown_sec=0)
    return backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                             entries=np.array([10, 20]), max_open=max_open,
                             min_stop=1.0)


def test_default_max_open_is_one_and_does_not_stack():
    res = _run(1)
    assert res.trades == 1


def test_max_open_two_takes_the_overlapping_second_fill():
    """Without the stacked path the second signal is skipped until the first exit."""
    res = _run(2)
    assert res.trades == 2
