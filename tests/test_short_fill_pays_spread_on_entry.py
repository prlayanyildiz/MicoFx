"""Short fills used to skip the spread; the stop check paid it instead.

Found in BR: long entry is ``open+s``, short entry was ``open``, and short
stops fired on ``high+s``. Each side paid the spread once but not at the
same place — longs got a worse fill, shorts got an easier stop. Live sells
at bid. Both legs now pay the spread on the fill; the stop reads raw OHLC.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def _short(spread: float):
    n = 80
    px = 100.0
    high = np.full(n, px)
    low = np.full(n, px)
    close = np.full(n, px)
    open_ = np.full(n, px)
    atr = np.full(n, 1.0)
    sell = np.zeros(n, dtype=bool)
    sell[10] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=np.zeros(n, dtype=bool), sell=sell,
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=2.0, trail_start_atr=0.0, cooldown_sec=0)
    # simulate() sizes from cache.atr_list, not sig.atr. Flat OHLC has ATR 0
    # and the ATR>0 gate skips the fill — same trap as the NaN-ATR core test.
    ones = np.ones(n)
    cache._atr[p.atr_period] = ones
    cache._atr_lists[p.atr_period] = ones.tolist()
    pts = np.full(n, spread / 0.01)  # point=0.01 → spread_price = pts * point
    return backtest.simulate(cache, sig, open_, pts, point=0.01, p=p,
                             entries=np.array([10]), min_stop=1.0)


def test_a_short_fill_pays_the_spread_the_same_way_a_long_does():
    """Time-exit at the same close: extra spread on the short fill is 1R here."""
    free = _short(0.0)
    taxed = _short(1.0)
    assert free.trades == 1 and taxed.trades == 1
    # sl_dist=2. With s=0, entry=100 exit=100 → 0R. With s=1, entry=99
    # cover=101 → −1R. The old short entry at 100 only paid spread on the
    # cover (−0.5R).
    assert abs(free.net_r - 0.0) < 1e-9
    assert taxed.net_r < -0.9
    assert taxed.net_r > -1.1
