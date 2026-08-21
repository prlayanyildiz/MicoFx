"""The stacked replay must be able to refuse a hedge, because the engine does.

With max_open > 1 the replay would open a position on the opposite side of an
existing one. risk.py refuses that outright ("ters yonde acik pozisyon var"),
so measuring a raised limit without the rule compares against a world we would
never run - and it is biased against the raised limit twice over: the hedge
loses on its own account, and it occupies the slot a same-direction entry
would otherwise have taken. On GER40's holdout the second slot held 1107
hedges against 598 pyramid entries, so it sat in the wrong trade about two
thirds of the time.

block_reverse defaults to False, so every measurement taken before this
option existed still means what it meant.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def _run(max_open: int, block_reverse: bool, second_is_sell: bool):
    n = 80
    high = np.full(n, 100.0)
    low = np.full(n, 99.2)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    low[40] = 90.0
    close[40] = 95.0
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    buy[10] = True
    if second_is_sell:
        sell[20] = True
    else:
        buy[20] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=sell,
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0, cooldown_sec=0)
    return backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                             entries=np.array([10, 20]), max_open=max_open,
                             block_reverse=block_reverse, min_stop=1.0)


def test_a_hedge_is_refused_when_the_live_rule_is_on():
    assert _run(2, block_reverse=False, second_is_sell=True).trades == 2
    assert _run(2, block_reverse=True, second_is_sell=True).trades == 1


def test_a_same_direction_entry_still_takes_the_second_slot():
    """The rule blocks hedging, not pyramiding - that distinction is the point."""
    assert _run(2, block_reverse=True, second_is_sell=False).trades == 2


def test_the_option_is_off_by_default_so_older_numbers_still_mean_what_they_meant():
    assert _run(2, block_reverse=False, second_is_sell=True).trades == 2
    assert _run(1, block_reverse=True, second_is_sell=False).trades == 1
    n = 80
    high = np.full(n, 100.0)
    low = np.full(n, 99.2)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    low[40] = 90.0
    close[40] = 95.0
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    buy[10] = True
    sell[20] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=sell,
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0, cooldown_sec=0)
    res = backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                            entries=np.array([10, 20]), max_open=2, min_stop=1.0)
    assert res.trades == 2
