"""Backtest must model live shakeout SL so WFO searches with the guard.

Live ``risk.shakeout_sl_atr_mult`` floors the *next* entry after 3 original-SL
deaths in the last 10 closes. Replay used to ignore that overlay — WFO picked
stops for a world where the guard never fires (EK24-B/C). Measurement only;
live exit constitution unchanged.
"""
from __future__ import annotations

import inspect

import numpy as np

from micofx import backtest
from micofx.risk import shakeout_sl_atr_mult
from micofx.strategy import IndicatorCache, Params, Signals

N = 400
ATR = 1.0
POINT = 0.01


def _force_atr(cache: IndicatorCache, period: int = 14) -> None:
    atr = cache.atr_list(period)
    for i in range(len(atr)):
        atr[i] = ATR
    cache._atr_lists[period] = atr


def _flat_book() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    high = np.full(N, 100.0)
    low = np.full(N, 100.0)
    close = np.full(N, 100.0)
    open_ = np.full(N, 100.0)
    return high, low, close, open_


def _run(buy_at: list[int], paint) -> object:
    high, low, close, open_ = _flat_book()
    paint(high, low, close, open_)
    buy = np.zeros(N, dtype=bool)
    for i in buy_at:
        buy[i] = True
    sig = Signals(
        t3=close, k=close, d=close, atr=np.full(N, ATR), adx=np.zeros(N),
        buy=buy, sell=np.zeros(N, dtype=bool),
        htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool),
    )
    cache = IndicatorCache(
        high, low, close, times=np.arange(N) * 300, tf_seconds=300,
        open_=open_, volume=np.ones(N),
    )
    p = Params(
        sl_atr_mult=1.0, trail_start_atr=10.0, trail_step_atr=1.0,
        cooldown_sec=0,
    )
    _force_atr(cache, p.atr_period)
    return backtest.simulate(
        cache, sig, open_, np.zeros(N), point=POINT, p=p,
        entries=np.array(buy_at, dtype=np.int64),
    )


def test_simulate_calls_the_live_shakeout_helper():
    assert "shakeout_sl_atr_mult" in inspect.getsource(backtest.simulate)


def test_three_original_stops_widen_the_next_entry():
    """After 3 hard-stop deaths, a 1.2 ATR dip must not kill the next long.

    Base SL is 1.0 ATR; shakeout bumps to 1.5. Without the model the 4th
    trade would also stop; with it the dip is inside the wider stop and the
    trade stays open to the sample end (time exit).
    """
    signals = [20, 40, 60, 80]

    def paint(high, low, close, open_):
        # Each of the first three: fill at open of signal+1, next bar wicks
        # through the 1.0 ATR hard stop.
        for sig_i in signals[:3]:
            j0 = sig_i + 1
            kill = j0 + 1
            low[kill] = 98.5
            close[kill] = 99.0
            high[kill] = 100.0
            open_[kill] = 100.0
        # 4th fill at 81; bar 82 dips 1.2 ATR (through 1.0, inside 1.5).
        j0 = signals[3] + 1
        dip = j0 + 1
        low[dip] = 100.0 - 1.2 * ATR
        close[dip] = 100.0 - 0.5 * ATR
        high[dip] = 100.0
        open_[dip] = 100.0
        # Hold flat afterward so a surviving trade ends as time, not trail.
        for j in range(dip + 1, N):
            open_[j] = close[dip]
            high[j] = close[dip]
            low[j] = close[dip]
            close[j] = close[dip]

    res = _run(signals, paint)
    assert res.trades == 4
    assert res.exits.get("stop") == 3
    # 4th survived the 1.2 ATR adverse print → not a 4th stop.
    assert res.exits.get("stop", 0) < 4
    assert res.trade_rs[3] > -1.0  # not a full original-SL death


def test_trail_exits_do_not_arm_shakeout():
    """Only original-SL deaths count — same rule as live autopsy ``exit_reason``."""
    signals = [20, 40, 60, 80]

    def paint(high, low, close, open_):
        # Three winners that trail out (never original stop).
        for sig_i in signals[:3]:
            j0 = sig_i + 1
            run = j0 + 1
            high[run] = 100.0 + 12.0  # past trail_start=10
            close[run] = 100.0 + 11.0
            open_[run] = 100.0
            low[run] = 100.0
            # Next bar collapses through the trail, not the original stop.
            kill = run + 1
            open_[kill] = close[run]
            high[kill] = close[run]
            low[kill] = 100.0
            close[kill] = 100.0
        # 4th: 1.2 ATR dip must still stop at base 1.0 (guard not armed).
        j0 = signals[3] + 1
        dip = j0 + 1
        low[dip] = 100.0 - 1.2 * ATR
        close[dip] = 99.0
        high[dip] = 100.0
        open_[dip] = 100.0

    res = _run(signals, paint)
    assert res.exits.get("trail", 0) >= 3
    assert res.exits.get("stop") == 1
    assert res.trade_rs[3] < 0


def test_bump_matches_live_helper_identity():
    """Paper bump is ``max(base, min(base*1.5, 2.0))`` — F8 relative floor."""
    assert shakeout_sl_atr_mult(
        1.0, "BT",
        [{"symbol": "BT", "exit_reason": "sl", "r_realised": -1.0}] * 3,
    ) == 1.5
