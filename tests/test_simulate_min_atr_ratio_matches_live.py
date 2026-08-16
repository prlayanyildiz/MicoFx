"""engine._try_entry gates on min_atr_ratio; simulate used to ignore it.

Found in BO: live ``engine.py`` refuses an entry when
``(atr / price_ref) < cfg.min_atr_ratio``. ``backtest.simulate`` had no such
check. Every live symbol is 0.0 today so paper and live still match, but a
nonzero value would silently split them. Both the sequential and stacked
(max_open>1) paths have to apply the same gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def _run(min_atr_ratio: float, max_open: int = 1):
    n = 80
    high = np.full(n, 100.0)
    low = np.full(n, 99.2)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
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
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0, cooldown_sec=0,
               min_atr_ratio=min_atr_ratio)
    return backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                             entries=np.array([10, 20]), max_open=max_open,
                             min_stop=1.0)


def test_zero_min_atr_ratio_still_fills():
    assert _run(0.0).trades == 1


def test_min_atr_ratio_above_atr_over_price_blocks_the_fill():
    """atr/price is 1/100=0.01; a 0.02 floor is the live engine's volatilite gate."""
    assert _run(0.02).trades == 0


def test_stacked_path_also_blocks_on_min_atr_ratio():
    assert _run(0.02, max_open=2).trades == 0
    assert _run(0.0, max_open=2).trades == 2
