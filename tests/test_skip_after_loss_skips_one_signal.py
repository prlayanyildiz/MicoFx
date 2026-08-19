"""skip_after_loss is gone from paper.

It lived only in simulate (four sites), never in the engine. CHOP-1b ran it
on the six live holdouts: all six lost R (GER40 −149). A flag the search
does not offer, live does not run, and holdout says is harmful, is a trap
for the next "let's try it" comparison — paper and live would silently
disagree.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def test_simulate_does_not_take_skip_after_loss():
    assert "skip_after_loss" not in inspect.signature(backtest.simulate).parameters
    src = inspect.getsource(backtest.simulate)
    assert "skip_after_loss" not in src
    assert "skip_next" not in src


def _run():
    n = 80
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    low[12] = 90.0
    close[12] = 95.0
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
                             entries=np.array([10, 30]))


def test_a_loss_does_not_drop_the_next_signal():
    """The live rule: both signals trade. That is what CHOP-1b scored."""
    res = _run()
    assert res.trades == 2
    assert res.losses == 1
