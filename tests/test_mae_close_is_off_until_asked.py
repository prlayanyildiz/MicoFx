"""LOSS-3: early MAE close is a measurement switch, default off.

Live does not exit on MAE. Search and walk_forward must not pass the
kwargs. A trade that dips then recovers is a winner today; the same path
closed on bar N is the counterfactual the measurement scores.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals

ENTRY_BAR = 30
N = 220
ATR = 1.0


def test_simulate_takes_mae_close_default_off():
    sig = inspect.signature(backtest.simulate)
    assert sig.parameters["mae_close_bars"].default == 0
    assert sig.parameters["mae_close_r"].default == 0.0
    src = inspect.getsource(backtest.walk_forward)
    assert "mae_close_bars" not in src
    assert "mae_close_r" not in src


def _dip_then_rally():
    """Fill near 100, 0.6R adverse on bar 2, then a 3 ATR rally. Stop never hits.

    ATR is the cache's Wilder series (simulate does not read Signals.atr), so
    the dip is sized from that number, not from a fake constant.
    """
    close = np.full(N, 100.0)
    high = np.full(N, 101.0)
    low = np.full(N, 99.0)
    open_ = np.full(N, 100.0)
    probe = IndicatorCache(high, low, close, times=np.arange(N) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(N))
    atr = float(probe.atr_list(14)[ENTRY_BAR])
    assert atr > 0.2
    fill = ENTRY_BAR + 1
    close[fill] = 100.1
    high[fill] = 100.4
    low[fill] = 99.8
    close[fill + 1] = 99.95
    high[fill + 1] = 100.2
    low[fill + 1] = 100.0 - 0.6 * atr
    close[fill + 2:] = np.linspace(100.3, 100.0 + 3.0 * atr, N - fill - 2)
    high[fill + 2:] = close[fill + 2:] + 0.4
    low[fill + 2:] = close[fill + 2:] - 0.4
    open_[0] = 100.0
    open_[1:] = close[:-1]
    open_ = np.clip(open_, low, high)
    return close, high, low, open_


def _run(*, mae_close_bars: int = 0, mae_close_r: float = 0.0):
    close, high, low, open_ = _dip_then_rally()
    buy = np.zeros(N, dtype=bool)
    buy[ENTRY_BAR] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(N, ATR), adx=np.zeros(N),
                  buy=buy, sell=np.zeros(N, dtype=bool),
                  htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(N) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(N))
    res = backtest.simulate(
        cache, sig, open_, np.zeros(N), point=0.01,
        p=Params(sl_atr_mult=1.0, trail_start_atr=0.0, trail_step_atr=1.6),
        entries=np.array([ENTRY_BAR]),
        mae_close_bars=mae_close_bars,
        mae_close_r=mae_close_r)
    assert res.trades == 1
    return res


def test_zero_bars_is_today_the_dip_recovers():
    res = _run(mae_close_bars=0, mae_close_r=0.5)
    assert res.exits.get("mae", 0) == 0
    assert res.trade_rs[0] > 1.0


def test_close_on_bar_two_cuts_the_recovery():
    res = _run(mae_close_bars=2, mae_close_r=0.5)
    assert res.exits.get("mae", 0) == 1
    assert res.trade_rs[0] == pytest.approx(-0.03, abs=0.15)
    assert res.trade_rs[0] < 0.5
