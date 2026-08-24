"""Per-trade cost/R is computed, then was thrown away.

Live refuses an entry when cost/R exceeds block_high_cost (18% on this
book). Paper charges the same ratio into the fill and refuses nothing, so
a holdout can contain trades live would never take. The per-trade value
was already on the _record_trade path; only the sum was kept.

This is the list, not a counterfactual P&L. Dropping the expensive trades
from a finished Result is not what live would have produced: no fill means
a different slot/cooldown/trail sequence. Report the share, do not rescore.

Claude 24.08 08:40: formula matches live once lot cancels; remaining gap
is tick spread vs bar spread (already measured, not this field).
"""
from __future__ import annotations

import numpy as np
import pytest

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def _one_loss():
    n = 60
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    low[12] = 90.0
    close[12] = 95.0
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0)
    return backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                             entries=np.array([10]))


def test_each_trade_keeps_the_cost_share_that_was_only_summed():
    res = _one_loss()
    assert res.trades == 1
    assert len(res.trade_cost_rs) == len(res.trade_rs) == 1
    assert res.trade_cost_rs[0] == pytest.approx(res.cost_r)
    assert res.trade_cost_rs[0] >= 0.0


def test_merged_results_keep_every_trade_cost():
    a, b = _one_loss(), _one_loss()
    merged = backtest._merge([a, b])
    assert len(merged.trade_cost_rs) == 2
    assert merged.cost_r == pytest.approx(sum(merged.trade_cost_rs))
