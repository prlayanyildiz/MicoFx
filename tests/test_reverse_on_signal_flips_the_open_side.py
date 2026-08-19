"""Opposite signal while open must close and reverse — but only when asked.

Live max_positions=1 drops the flip: the new signal dies on the slot cap and
the old trade waits for its stop. REV-1 measures the other rule on paper.
Default stays the live rule; a flag that is off must not change a number.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def _run(reverse: bool, max_open: int = 1):
    n = 80
    high = np.full(n, 100.4)
    # Range ~0.8 so Wilder ATR is live; min_stop=1 keeps SL at 99, under this low.
    low = np.full(n, 99.6)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    # Buy fills at 11 and would wait for a stop at 40. Sell at 20 fills at 21
    # while that long is still open.
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
    return backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                             entries=np.array([10, 20]), max_open=max_open,
                             min_stop=1.0, reverse_on_signal=reverse)


def test_default_drops_the_opposite_signal_and_waits_for_the_stop():
    res = _run(False)
    assert res.trades == 1, f"varsayilan ters sinyali isleme cevirdi n={res.trades}"
    assert res.exits.get("reverse", 0) == 0
    assert res.exits.get("stop", 0) == 1


def test_reverse_flag_closes_the_open_side_and_takes_the_flip():
    res = _run(True)
    assert res.trades == 2, f"donus iki islem yazmadi n={res.trades}"
    assert res.exits.get("reverse", 0) == 1, "ilk bacak reverse ile kapanmadi"
    assert "reverse_on_signal" in backtest.simulate.__code__.co_varnames


def test_reverse_flag_does_the_same_on_the_stacked_path():
    res = _run(True, max_open=2)
    assert res.exits.get("reverse", 0) == 1
    assert res.trades >= 2
