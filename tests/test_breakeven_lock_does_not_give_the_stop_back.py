"""BE-1: a lock at entry, independent of the trail.

The trail crosses entry only after gain exceeds trail_step_atr
(test_trail_breakeven_invariant). Autopsy rows then show a GER40 trade at
+1.42 R closing −1.00 R because trail_step (2.2) is wider than the stop (1.0).

``breakeven_at_r=0`` is the dataclass default (off). Live rows set 1.5
(operator 25.08). Search does not sweep it (not an OPT_FIELD). walk_forward
does not pass the simulate kwarg — Params.from_config carries the field.
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
N = 260


def test_simulate_kwarg_defaults_to_params():
    sig = inspect.signature(backtest.simulate)
    assert "breakeven_at_r" in sig.parameters
    assert sig.parameters["breakeven_at_r"].default is None
    src = inspect.getsource(backtest.walk_forward)
    assert "breakeven_at_r" not in src


def _ramp_then_collapse(peak_atr: float):
    close = np.empty(N)
    close[:ENTRY_BAR + 1] = 100.0
    up_end = ENTRY_BAR + 60
    close[ENTRY_BAR + 1:up_end] = np.linspace(100.0, 100.0 + peak_atr,
                                              up_end - ENTRY_BAR - 1)
    close[up_end:] = np.linspace(100.0 + peak_atr, 80.0, N - up_end)
    open_ = np.empty(N)
    open_[0] = close[0]
    open_[1:] = close[:-1]
    high = close + 0.5
    low = close - 0.5
    open_ = np.clip(open_, low, high)
    return close, high, low, open_


def _run(peak_atr: float, *, start: float = 0.0, step: float = 1.6,
         breakeven_at_r: float = 0.0, via_params: bool = False):
    close, high, low, open_ = _ramp_then_collapse(peak_atr)
    buy = np.zeros(N, dtype=bool)
    buy[ENTRY_BAR] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(N, 1.0), adx=np.zeros(N),
                  buy=buy, sell=np.zeros(N, dtype=bool),
                  htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(N) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(N))
    p = Params(sl_atr_mult=1.0, trail_start_atr=start, trail_step_atr=step,
               breakeven_at_r=breakeven_at_r if via_params else 0.0)
    kwargs = {} if via_params else {"breakeven_at_r": breakeven_at_r}
    res = backtest.simulate(
        cache, sig, open_, np.zeros(N), point=0.01, p=p,
        entries=np.array([ENTRY_BAR]), **kwargs)
    assert res.trades == 1
    return res.trade_rs[0]


def test_zero_is_today_the_stop_is_given_back():
    """Trail off, peak past 1R, collapse: live outcome is −1R."""
    assert _run(1.5, start=0.0, breakeven_at_r=0.0) == pytest.approx(-1.0, abs=0.05)


def test_a_one_r_lock_keeps_the_winner_near_zero():
    """Same path, lock at 1R: stop comes to entry instead of giving 1R back."""
    r = _run(1.5, start=0.0, breakeven_at_r=1.0)
    assert r == pytest.approx(0.0, abs=0.08)


def test_params_field_is_enough_without_the_kwarg():
    """walk_forward never passes the kwarg; Params.from_config must be enough."""
    r = _run(1.5, start=0.0, breakeven_at_r=1.0, via_params=True)
    assert r == pytest.approx(0.0, abs=0.08)


def test_a_better_trail_is_kept():
    """Lock must not pull a trail that is already past entry back to entry."""
    off = _run(3.0, start=0.5, step=1.6, breakeven_at_r=0.0)
    locked = _run(3.0, start=0.5, step=1.6, breakeven_at_r=1.0)
    assert off > 1.0
    assert locked == pytest.approx(off, abs=1e-9)
