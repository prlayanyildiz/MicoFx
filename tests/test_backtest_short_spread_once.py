"""Non-stop exits must charge one round-trip spread on both sides.

Entry already embeds the open-side quote (buy ask = open+s, sell bid =
open-s). Flatten / time / reverse exits that add ``+s`` again on shorts
pay the spread twice; the matching long pays once. That is OPTIMIZATIONS
B3 — costed WFO then systematically under-ranks short paths.

Stop fills are a different door (exit at SL; pad is trigger-only) and
already covered by ``test_short_stop_triggers_on_ask``. This fixture keeps
ask (high+pad) below the short SL so flatten/reverse actually run.
"""
from __future__ import annotations

import numpy as np

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals

N = 80
SIGNAL = 10
FILL = SIGNAL + 1
FLAT = FILL + 2
PX = 100.0
POINT = 0.01
SPREAD = 1.0  # price units = full ask-bid
SL_MULT = 2.0  # wide: flatten/reverse before any stop
# Long SL = (PX+SPREAD)-SL_MULT = 99 → keep low > 99.
# Short SL = (PX-SPREAD)+SL_MULT = 101 → keep high+SPREAD < 101.
SAFE_MID = 99.5


def _side(is_buy: bool, *, reverse: bool = False):
    high = np.full(N, SAFE_MID)
    low = np.full(N, SAFE_MID)
    close = np.full(N, PX)
    open_ = np.full(N, PX)
    buy = np.zeros(N, dtype=bool)
    sell = np.zeros(N, dtype=bool)
    if is_buy:
        buy[SIGNAL] = True
    else:
        sell[SIGNAL] = True
    if reverse:
        if is_buy:
            sell[FLAT - 1] = True
        else:
            buy[FLAT - 1] = True
    flatten = np.zeros(N, dtype=bool)
    if not reverse:
        flatten[FLAT] = True
    atr = np.full(N, 1.0)
    sig = Signals(
        t3=close, k=close, d=close, atr=atr, adx=np.zeros(N),
        buy=buy, sell=sell,
        htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool),
    )
    cache = IndicatorCache(
        high, low, close, times=np.arange(N) * 300, tf_seconds=300,
        open_=open_, volume=np.ones(N),
    )
    p = Params(sl_atr_mult=SL_MULT, trail_start_atr=0.0, cooldown_sec=0,
               atr_period=14)
    ones = np.ones(N)
    cache._atr[p.atr_period] = ones
    cache._atr_lists[p.atr_period] = ones.tolist()
    pts = np.full(N, SPREAD / POINT)
    return backtest.simulate(
        cache, sig, open_, pts, point=POINT, p=p,
        entries=np.array([SIGNAL]), min_stop=0.1,
        flatten=None if reverse else flatten,
        reverse_on_signal=reverse,
    )


def test_flatten_charges_one_spread_on_long_and_short():
    long = _side(True)
    short = _side(False)
    assert long.exits.get("flatten") == 1, long.exits
    assert short.exits.get("flatten") == 1, short.exits
    expect = -SPREAD / SL_MULT  # -0.5R
    assert abs(long.trade_rs[0] - expect) < 1e-9, f"long R={long.trade_rs[0]}"
    assert abs(short.trade_rs[0] - expect) < 1e-9, (
        f"short flatten R={short.trade_rs[0]}, want {expect}; "
        f"price drag={short.trade_rs[0] * SL_MULT}"
    )


def test_reverse_cover_charges_one_spread_on_short():
    long = _side(True, reverse=True)
    short = _side(False, reverse=True)
    assert long.exits.get("reverse", 0) >= 1, long.exits
    assert short.exits.get("reverse", 0) >= 1, short.exits
    expect = -SPREAD / SL_MULT
    assert abs(long.trade_rs[0] - expect) < 1e-9
    assert abs(short.trade_rs[0] - expect) < 1e-9, (
        f"short reverse R={short.trade_rs[0]}, want {expect}"
    )


def test_time_exit_charges_one_spread_on_short():
    """End-of-sample path (no flatten) must also stay one-spread."""
    high = np.full(N, SAFE_MID)
    low = np.full(N, SAFE_MID)
    close = np.full(N, PX)
    open_ = np.full(N, PX)
    sell = np.zeros(N, dtype=bool)
    sell[SIGNAL] = True
    atr = np.full(N, 1.0)
    sig = Signals(
        t3=close, k=close, d=close, atr=atr, adx=np.zeros(N),
        buy=np.zeros(N, dtype=bool), sell=sell,
        htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool),
    )
    cache = IndicatorCache(
        high, low, close, times=np.arange(N) * 300, tf_seconds=300,
        open_=open_, volume=np.ones(N),
    )
    p = Params(sl_atr_mult=SL_MULT, trail_start_atr=0.0, cooldown_sec=0,
               atr_period=14)
    ones = np.ones(N)
    cache._atr[p.atr_period] = ones
    cache._atr_lists[p.atr_period] = ones.tolist()
    # No flatten/stop → end-of-sample time exit (needs n-lo >= 50).
    res = backtest.simulate(
        cache, sig, open_, np.full(N, SPREAD / POINT), point=POINT, p=p,
        entries=np.array([SIGNAL]), min_stop=0.1,
    )
    assert res.exits.get("time") == 1, res.exits
    expect = -SPREAD / SL_MULT
    assert abs(res.trade_rs[0] - expect) < 1e-9, res.trade_rs
