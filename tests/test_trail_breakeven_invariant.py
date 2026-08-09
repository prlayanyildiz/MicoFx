"""When the trail reaches breakeven, and why `trail_start <= trail_step` is fine.

A hard-scan of this repo reported `trail_start_atr <= trail_step_atr` as a
critical bug ("the stop stays below entry, natural breakeven is a lie") and
proposed rejecting those combinations in the optimizer, the grids and apply
validation. That would have been wrong and would have made 14 live symbols
worse. These tests pin down the real behaviour so the claim cannot come back.

The actual invariant:

    the trail sits at `close - trail_step_atr * ATR`,
    so it is above entry exactly when profit > trail_step_atr * ATR

which has nothing to do with `trail_start_atr`. All `trail_start_atr` decides
is how early the trail begins tightening the stop *below* entry.

`simulate()` derives ATR from the bar series itself (`cache.atr_list`), not
from `sig.atr`, so the fixtures build bars spanning ~1.0 to make one ATR equal
one price unit and keep the numbers readable.
"""
from __future__ import annotations

import numpy as np
import pytest

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals

ENTRY_BAR = 30
N = 260


def _ramp_then_collapse(peak_atr: float):
    """Flat, then a climb of `peak_atr`, then straight down through the stop."""
    close = np.empty(N)
    close[:ENTRY_BAR + 1] = 100.0
    up_end = ENTRY_BAR + 60
    close[ENTRY_BAR + 1:up_end] = np.linspace(100.0, 100.0 + peak_atr,
                                              up_end - ENTRY_BAR - 1)
    close[up_end:] = np.linspace(100.0 + peak_atr, 80.0, N - up_end)
    return close, close + 0.5, close - 0.5      # bar span 1.0 -> ATR ~= 1.0


def _run(sl_mult: float, start: float, step: float, peak_atr: float):
    close, high, low = _ramp_then_collapse(peak_atr)
    open_ = np.full(N, 100.0)
    buy = np.zeros(N, dtype=bool)
    buy[ENTRY_BAR] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(N, 1.0), adx=np.zeros(N),
                  buy=buy, sell=np.zeros(N, dtype=bool),
                  htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(N) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(N))
    res = backtest.simulate(
        cache, sig, open_, np.zeros(N), point=0.01,
        p=Params(sl_atr_mult=sl_mult, trail_start_atr=start, trail_step_atr=step),
        entries=np.array([ENTRY_BAR]))
    assert res.trades == 1
    return res.trade_rs[0]


def test_atr_fixture_is_one_price_unit():
    """Guard the fixture itself - every threshold below is stated in ATR."""
    close, high, low = _ramp_then_collapse(5.0)
    cache = IndicatorCache(high, low, close, times=np.arange(N) * 300,
                           tf_seconds=300, open_=np.full(N, 100.0), volume=np.ones(N))
    assert 0.95 <= cache.atr_list(14)[ENTRY_BAR] <= 1.05


@pytest.mark.parametrize("start,step", [
    (0.5, 1.6),     # NAS100 / JPN225 / SPA35, live
    (0.5, 1.2),     # GER40, live
    (0.3, 0.8),     # XAUUSD, live
    (0.4, 0.4),     # USDCHF, live - start == step
    (2.0, 1.6),     # "compliant" start > step
    (1.0, 0.4),     # "compliant" start > step
])
def test_breakeven_is_reached_at_trail_step_regardless_of_trail_start(start, step):
    """Profit past `trail_step` ATR always leaves the stop above entry."""
    # Comfortably past the threshold so the discrete bar grid cannot straddle it.
    assert _run(1.0, start, step, peak_atr=step + 1.0) > 0, \
        f"start={start} step={step}: stop never crossed entry"
    # ...and comfortably short of it, the trade still gives risk back, which is
    # what makes the threshold above meaningful rather than trivially true.
    if step > 0.6:
        assert _run(1.0, start, step, peak_atr=step - 0.5) < 0


def test_start_below_step_is_never_worse_than_start_above_step():
    """The reported "bug" is strictly better before breakeven, equal after.

    Same trail distance (1.6), same hard stop; only the arming point differs.
    If this ever inverts, the grid rule the hard scan asked for might be worth
    revisiting - until then it would only delay risk reduction.
    """
    for peak in (1.0, 1.5, 2.0, 3.0):
        early = _run(1.0, 0.5, 1.6, peak)     # start < step
        late = _run(1.0, 2.0, 1.6, peak)      # start > step
        assert early >= late - 1e-9, (
            f"peak={peak}: start<step ({early:+.2f}R) came out worse than "
            f"start>step ({late:+.2f}R)")
    # And it is genuinely better somewhere, not just never worse.
    assert _run(1.0, 0.5, 1.6, 1.5) > _run(1.0, 2.0, 1.6, 1.5)


def test_trail_never_lands_worse_than_the_hard_stop():
    """The ratchet floor: -1R is the worst case whatever the trail asks for."""
    for start, step in ((0.5, 1.6), (0.1, 3.0), (0.4, 0.4)):
        r = _run(1.0, start, step, peak_atr=0.25)   # barely moves, then dies
        assert r >= -1.01, f"start={start} step={step} lost more than 1R: {r:+.2f}"


def test_optimizer_grids_do_not_filter_on_start_vs_step():
    """No hidden rule rejecting start <= step crept into the shipped grids.

    The shared grid is deliberately allowed to pair any start with any step;
    this asserts the pairing exists rather than that it is merely permitted.
    """
    from micofx.paths import load_defaults
    grid = load_defaults()["optimizer"]["grid"]
    starts, steps = grid["trail_start_atr"], grid["trail_step_atr"]
    pairs = [(a, b) for a in starts for b in steps if a <= b]
    assert pairs, "shipped grid can no longer express start <= step"


def test_trail_start_zero_disables_the_trail_entirely():
    """Pins the surprising semantics the API bound now guards against.

    Documented rather than changed: `if trail_start_atr > 0` is shared by the
    engine and the simulator, so altering it here would be an exit-model change.
    What matters is that the behaviour is known and deliberately unreachable
    from outside - see test_symbol_risk_bounds.py, which rejects 0 at the API.
    """
    # A run that reaches +3 ATR and collapses. With a working trail this banks
    # profit (see the parametrised test above); with trail_start 0 it does not
    # arm at all and the whole 1R of hard-stop risk is given back.
    assert _run(1.0, 0.0, 1.6, peak_atr=3.0) == pytest.approx(-1.0, abs=0.02)
    assert _run(1.0, 0.5, 1.6, peak_atr=3.0) > 1.0
