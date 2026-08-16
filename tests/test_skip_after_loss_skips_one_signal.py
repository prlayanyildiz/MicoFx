"""A losing close must skip the next signal, not N bars.

Found in 417 book-magic deals (split-replicated): after a win WR 49.3% /
+4.13$, after a loss 28% / −2.91$. N-bar pause failed holdout (AY2). The
event form is: skip exactly one following signal, then resume.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def _run(skip: bool):
    n = 80
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    # First signal at 10: fill 11, stop-out at 12.
    low[12] = 90.0
    close[12] = 95.0
    # Second signal at 30: fill 31, winner — price never hits a 1-ATR stop.
    high[40] = 104.0
    close[40] = 104.0
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    buy[30] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0)
    return backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                             entries=np.array([10, 30]), skip_after_loss=skip)


def test_without_the_rule_both_signals_trade():
    res = _run(False)
    assert res.trades == 2
    assert res.losses == 1


def test_a_loss_skips_the_next_signal():
    """The second bar is a winner; taking it is what the live cluster forbids."""
    res = _run(True)
    assert res.trades == 1
    assert res.losses == 1
