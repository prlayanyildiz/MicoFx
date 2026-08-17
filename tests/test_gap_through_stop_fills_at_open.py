"""A gap that opens through the stop must fill at open, not at the SL.

Live a stop sitting below Friday's close is filled near Monday's open when
the bar gaps through it. backtest._exit_check (and the max_open==1 copy)
books the SL anyway, which is the gift GAP-1 measured at 8% of book holdout
net R and 49% of FRA40's.

Trigger is unchanged: long still fires on bar_low <= SL, short on
bar_high + pad >= SL (e0e121c). Only the fill price moves, and only when
the bar's open is already through the SL. Flatten/time still use close.
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
ATR = 1.0
SL_MULT = 1.0


def _cache(high, low, close, open_, buy=None, sell=None):
    buy = np.zeros(N, dtype=bool) if buy is None else buy
    sell = np.zeros(N, dtype=bool) if sell is None else sell
    sig = Signals(t3=close, k=close, d=close, atr=np.full(N, ATR), adx=np.zeros(N),
                  buy=buy, sell=sell,
                  htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(N) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(N))
    ones = np.full(N, ATR)
    p = Params(sl_atr_mult=SL_MULT, trail_start_atr=0.0, cooldown_sec=0, atr_period=14)
    cache._atr[p.atr_period] = ones
    cache._atr_lists[p.atr_period] = ones.tolist()
    return cache, sig, p


def _long_gap(open_at_trap: float, low_at_trap: float, max_open: int = 1):
    """Long fill at 100, SL at 99. Trap bar opens through the SL."""
    high = np.full(N, PX)
    low = np.full(N, PX)
    close = np.full(N, PX)
    open_ = np.full(N, PX)
    open_[FILL] = PX
    high[FILL] = PX
    low[FILL] = PX
    close[FILL] = PX
    open_[TRAP] = open_at_trap
    high[TRAP] = max(open_at_trap, PX)
    low[TRAP] = low_at_trap
    close[TRAP] = low_at_trap
    buy = np.zeros(N, dtype=bool)
    buy[SIGNAL] = True
    cache, sig, p = _cache(high, low, close, open_, buy=buy)
    return backtest.simulate(
        cache, sig, open_, np.zeros(N), point=POINT, p=p,
        entries=np.array([SIGNAL]), min_stop=0.1, max_open=max_open,
    )


def _short_gap(open_at_trap: float, high_at_trap: float, spread: float = 0.0):
    """Short fill at 100 (spread 0) → SL 101. Trap bar opens through the SL."""
    high = np.full(N, PX)
    low = np.full(N, PX)
    close = np.full(N, PX)
    open_ = np.full(N, PX)
    open_[FILL] = PX
    high[FILL] = PX
    low[FILL] = PX
    close[FILL] = PX
    open_[TRAP] = open_at_trap
    high[TRAP] = high_at_trap
    low[TRAP] = min(open_at_trap, PX)
    close[TRAP] = open_at_trap
    sell = np.zeros(N, dtype=bool)
    sell[SIGNAL] = True
    cache, sig, p = _cache(high, low, close, open_, sell=sell)
    pts = np.full(N, spread / POINT)
    return backtest.simulate(
        cache, sig, open_, pts, point=POINT, p=p,
        entries=np.array([SIGNAL]), min_stop=0.1,
    )


def test_a_long_gap_through_the_stop_fills_at_open_not_sl():
    """Prev close 100, SL 99, open 97. Paper today books -1R at the SL."""
    res = _long_gap(open_at_trap=97.0, low_at_trap=96.0)
    assert res.trades == 1
    assert res.exits.get("stop", 0) == 1
    r = res.trade_rs[0]
    # entry 100, sl_dist 1, fill 97 → -3R. SL fill would be -1R.
    assert abs(r - (-3.0)) < 0.05, (
        f"long gap fill R={r}; SL hediyesi -1.0, acilis filli -3.0 olmali"
    )


def test_a_short_gap_through_the_stop_fills_at_open_not_sl():
    """SL 101, open 103. Trigger pad stays on the trigger; fill is open."""
    res = _short_gap(open_at_trap=103.0, high_at_trap=104.0)
    assert res.trades == 1
    assert res.exits.get("stop", 0) == 1
    r = res.trade_rs[0]
    # entry 100, sl_dist 1, fill 103 → -3R. SL fill would be -1R.
    assert abs(r - (-3.0)) < 0.05, (
        f"short gap fill R={r}; SL hediyesi -1.0, acilis filli -3.0 olmali"
    )


def test_an_intrabar_stop_still_fills_at_the_sl():
    """Open stays on the safe side of the SL; the wick tags it. Fill stays SL."""
    res = _long_gap(open_at_trap=99.5, low_at_trap=98.0)
    assert res.trades == 1
    assert abs(res.trade_rs[0] - (-1.0)) < 0.05, (
        f"intrabar R={res.trade_rs[0]}; wick SL'de kalmali, acilista degil"
    )


def test_gap_fill_also_applies_on_the_stacked_max_open_path():
    res = _long_gap(open_at_trap=97.0, low_at_trap=96.0, max_open=2)
    assert res.trades == 1
    assert abs(res.trade_rs[0] - (-3.0)) < 0.05, (
        f"max_open path R={res.trade_rs[0]}; _exit_check hâlâ SL yaziyor"
    )
