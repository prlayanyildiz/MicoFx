"""Short stop trigger must see the ask, not the bid high.

Live covers a short when ask trades at the SL. Paper OHLC is bid, so the
live condition is ``bar_high + spread >= sl``. a5562e9 moved the spread
onto the fill (correct as a cost) and left the trigger on raw high
(wrong as a trigger). The two are not the same thing.

Fail-first: a bar whose bid high sits just under the SL, but whose ask
(high + spread) is through it, must stop. Exit price stays the SL — the
spread in the trigger is a price reference, not a second charge.
"""
from __future__ import annotations

import numpy as np

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals

N = 80
SIGNAL = 10
FILL = SIGNAL + 1
TRAP = FILL + 1
PX = 100.0
POINT = 0.01
SPREAD = 1.0  # price units
SL_MULT = 1.5


def _short(high_at_trap: float, spread: float = SPREAD):
    high = np.full(N, PX)
    low = np.full(N, PX)
    close = np.full(N, PX)
    open_ = np.full(N, PX)
    # Fill bar: ask (high+s) stays below the SL so the trap is the next bar.
    # entry = 100 - 1 = 99, sl = 99 + 1.5 = 100.5 → fill high must be < 99.5.
    open_[FILL] = PX
    high[FILL] = 99.4
    low[FILL] = 99.0
    close[FILL] = 99.8
    open_[TRAP] = PX
    high[TRAP] = high_at_trap
    low[TRAP] = 99.0
    close[TRAP] = 99.8
    sell = np.zeros(N, dtype=bool)
    sell[SIGNAL] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(N, 1.0), adx=np.zeros(N),
                  buy=np.zeros(N, dtype=bool), sell=sell,
                  htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(N) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(N))
    p = Params(sl_atr_mult=SL_MULT, trail_start_atr=0.0, cooldown_sec=0, atr_period=14)
    ones = np.ones(N)
    cache._atr[p.atr_period] = ones
    cache._atr_lists[p.atr_period] = ones.tolist()
    pts = np.full(N, spread / POINT)
    return backtest.simulate(
        cache, sig, open_, pts, point=POINT, p=p,
        entries=np.array([SIGNAL]), min_stop=0.1,
    )


def test_a_short_stop_fires_when_ask_clears_the_sl_but_bid_high_does_not():
    """bid high 100, SL 100.5, spread 1 → ask 101. Paper today does not stop."""
    res = _short(high_at_trap=100.0)
    assert res.trades == 1
    _entry, exit_ts, r = res.trade_events[0]
    assert exit_ts == TRAP * 300, (
        f"short stop tetiklenmedi (cikis {exit_ts}, tuzak {TRAP * 300}, "
        f"exits={res.exits}). bar_high < SL <= bar_high+spread iken kagit "
        f"ask'e bakmiyor"
    )
    # Exit price is the SL (100.5), not SL+spread. entry 99, sl_dist 1.5 → -1R.
    assert abs(r - (-1.0)) < 0.05, (
        f"cikis R={r}; SL'den degilse spread ikinci kez alinmis demektir"
    )
    assert res.exits.get("stop", 0) == 1


def test_a_long_stop_still_reads_bid_low_not_bid_minus_spread():
    """The long corner is already the bid. Subtracting spread would fire early."""
    n = N
    high = np.full(n, PX)
    low = np.full(n, PX)
    close = np.full(n, PX)
    open_ = np.full(n, PX)
    open_[FILL] = PX
    high[FILL] = 100.2
    low[FILL] = 99.8
    close[FILL] = 100.1
    # SL ≈ 101 - 1.5 = 99.5 (entry is open+s). low=99.7 is above SL;
    # low - spread = 98.7 would be through it. Must not stop.
    open_[TRAP] = PX
    high[TRAP] = 100.2
    low[TRAP] = 99.7
    close[TRAP] = 99.9
    buy = np.zeros(n, dtype=bool)
    buy[SIGNAL] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(n, 1.0), adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=SL_MULT, trail_start_atr=0.0, cooldown_sec=0)
    ones = np.ones(n)
    cache._atr[p.atr_period] = ones
    cache._atr_lists[p.atr_period] = ones.tolist()
    pts = np.full(n, SPREAD / POINT)
    res = backtest.simulate(
        cache, sig, open_, pts, point=POINT, p=p,
        entries=np.array([SIGNAL]), min_stop=0.1,
    )
    assert res.trades == 1
    _entry, exit_ts, _r = res.trade_events[0]
    assert exit_ts != TRAP * 300, (
        f"long stop tuzak barda cikiyor; bid-spread'e bakiliyor olabilir. "
        f"exits={res.exits}"
    )
