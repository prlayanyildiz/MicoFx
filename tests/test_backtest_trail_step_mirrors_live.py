"""The replay's trail must not ratchet closer than live's throttle allows.

engine._update_stop refuses to send a modify for an improvement smaller than
``trail_min_step`` - live needs that so a slow drift does not put an order on
the wire every poll for a fraction of a point.

backtest.simulate had no such floor and moved the stop on any improvement at
all. So the simulated trail rode closer behind price than live's ever can, and
gave back less on the reversal that ends the trade. That is optimism in one
direction only, in exactly the figures the apply gates read - net_r, expectancy,
the holdout score - and net_r is what risk._edge_metric turns into a live lot
multiplier.

Both now call the same function, so they cannot drift apart again.
"""
from __future__ import annotations

import inspect

import numpy as np
import pytest

from micofx import backtest
from micofx import engine as engine_mod
from micofx.models import trail_min_step
from micofx.strategy import IndicatorCache, Params, Signals

N = 260
ENTRY_BAR = 30


def _creep_then_collapse(peak_atr: float, creep_bars: int = 60):
    """Climb of ``peak_atr`` spread over many bars, then straight down."""
    close = np.empty(N)
    close[:ENTRY_BAR + 1] = 100.0
    up_end = ENTRY_BAR + creep_bars
    close[ENTRY_BAR + 1:up_end] = np.linspace(100.0, 100.0 + peak_atr,
                                              up_end - ENTRY_BAR - 1)
    close[up_end:] = np.linspace(100.0 + peak_atr, 80.0, N - up_end)
    open_ = np.empty(N)
    open_[0] = close[0]
    open_[1:] = close[:-1]
    high = close + 0.5
    low = close - 0.5
    # Keep the bar span at 1.0 (ATR ≈ 1) while the open follows the previous
    # close. A constant open of 100 made every collapse bar a gap through the
    # trailed SL; live would fill that at the open, which is not what these
    # tests are measuring.
    open_ = np.clip(open_, low, high)
    return close, high, low, open_


def _run(peak_atr: float, trail_step: float, sl_mult: float = 1.0,
         trail_start: float = 0.5):
    close, high, low, open_ = _creep_then_collapse(peak_atr)
    buy = np.zeros(N, dtype=bool)
    buy[ENTRY_BAR] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(N, 1.0), adx=np.zeros(N),
                  buy=buy, sell=np.zeros(N, dtype=bool),
                  htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(N) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(N))
    res = backtest.simulate(
        cache, sig, open_, np.zeros(N), point=0.01,
        p=Params(sl_atr_mult=sl_mult, trail_start_atr=trail_start,
                 trail_step_atr=trail_step),
        entries=np.array([ENTRY_BAR]))
    assert res.trades == 1
    return res.trade_rs[0]


# ------------------------------------------------------------- the shared floor

def test_both_sides_use_the_same_step_function():
    # Structural, not behavioural: the two implementations drifted apart once
    # already because the number was written out twice. Neither may go back to
    # computing its own.
    assert "trail_min_step" in inspect.getsource(engine_mod.Engine._update_stop)
    assert "trail_min_step" in inspect.getsource(backtest.simulate)


def test_both_sides_use_the_shared_overlay_stop():
    from micofx.exits import overlay_stop
    assert "overlay_stop" in inspect.getsource(engine_mod.Engine._update_stop)
    assert "overlay_stop" in inspect.getsource(backtest.simulate)
    assert overlay_stop(
        is_buy=True, entry=100.0, ref=102.0, atr=1.0,
        trail_start_atr=0.5, trail_step_atr=1.0, trail_mode="atr",
        struct_sl=None, breakeven_at_r=0.0, original_risk=1.0,
    ) == pytest.approx(101.0)


def test_step_is_the_larger_of_the_broker_floor_and_the_atr_fraction():
    # Broker floor dominates when ATR is tiny...
    assert trail_min_step(min_stop=4.0, atr=0.1, trail_step_atr=1.0) == pytest.approx(1.0)
    # ...and the ATR fraction when the instrument is moving.
    assert trail_min_step(min_stop=0.4, atr=10.0, trail_step_atr=1.6) == pytest.approx(1.6)


# --------------------------------------------------- the throttle actually bites

@pytest.mark.parametrize("peak,step,expected", [
    # Hand-checked against the replay: these are the scenarios where the floor
    # changes the outcome, i.e. where the old replay was reporting more R than
    # live could have produced.
    (2.0, 0.8, 1.1655),
    (3.0, 1.6, 1.2448),
    (5.0, 1.6, 3.3138),
])
def test_throttled_trail_gives_the_live_reachable_result(peak, step, expected):
    assert _run(peak, step) == pytest.approx(expected, abs=1e-3)


@pytest.mark.parametrize("peak,step", [(2.0, 1.6), (3.0, 0.8), (5.0, 0.8)])
def test_scenarios_the_floor_does_not_reach_are_unchanged(peak, step):
    # The floor must be a floor, not a general drag: where every ratchet was
    # already larger than one step, the result is exactly what it always was.
    unthrottled = {(2.0, 1.6): 0.4, (3.0, 0.8): 2.2, (5.0, 0.8): 4.2}
    assert _run(peak, step) == pytest.approx(unthrottled[(peak, step)], abs=1e-3)


def test_the_throttle_never_flatters_a_trade():
    # The whole point: the floor can only ever cost R, never add it. A replay
    # that came out BETTER for having a throttle would mean it is modelling
    # something other than a delayed ratchet.
    for peak in (1.5, 2.0, 2.5, 3.0, 4.0, 5.0):
        for step in (0.4, 0.8, 1.2, 1.6):
            # Ratcheting later can only ever leave the stop further from price.
            assert _run(peak, step) <= peak - step + 1e-6


# --------------------------------------------------------- invariants unchanged

def test_the_hard_stop_floor_still_holds():
    for step in (0.4, 0.8, 1.6):
        assert _run(0.25, step) >= -1.01


def test_breakeven_is_still_reached_past_one_trail_step():
    for step in (0.4, 0.8, 1.6):
        assert _run(step + 1.0, step) > 0
