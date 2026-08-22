"""Cooldown is the same clamp on both simulate arms, and it is a no-op on M5.

Live waits ``cooldown_sec`` wall-clock seconds after a fill, capped at one
or two bars of the symbol TF (``engine._cooldown_for``). Paper turns that
into a bar count (``_cooldown_bars``).

Two facts, both easy to misread:

* The sequential arm (max_open=1) does apply it - after the exit, as a skip
  of later signal bars. It has no ``cool_until`` because it cannot overlap.
  The stacked arm applies the same count from the fill, because it can.
* On this book the configured 120s is shorter than an M5 bar, so the bar
  count is zero. A search at M5/M15/M30 is therefore cooldown-free even
  though live still waits 120s; the next bar arrives after that wait. M1
  is where the count becomes 2 and the rule can bind.

The sequential arm used to duplicate the clamp instead of calling the
helper. That is why a grep for ``cool_until`` looked like the rule was
missing. The helper is shared; the numbers this file pins did not change.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def _run(tf_seconds: int, cooldown_sec: int, signals: list[int],
         max_open: int, stop_at: int | None = 40) -> backtest.Result:
    n = 80
    high = np.full(n, 100.0)
    low = np.full(n, 99.2)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    if stop_at is not None:
        low[stop_at] = 90.0
        close[stop_at] = 95.0
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    for i in signals:
        buy[i] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * tf_seconds,
                           tf_seconds=tf_seconds, open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0, cooldown_sec=cooldown_sec)
    return backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                             entries=np.array(signals), max_open=max_open,
                             min_stop=1.0)


def test_stacked_m1_drops_a_signal_inside_the_two_bar_pause():
    """120s on a 60s bar is two bars. Fill at 11 cools through signal bar 12."""
    blocked = _run(60, 120, [10, 11], max_open=2)
    open_ = _run(60, 0, [10, 11], max_open=2)
    assert blocked.trades == 1
    assert open_.trades == 2


def test_stacked_m1_takes_the_signal_after_the_pause():
    assert _run(60, 120, [10, 13], max_open=2).trades == 2


def test_sequential_m1_drops_a_reentry_inside_the_remainder():
    """Same-bar stop: the hold does not eat the pause, so the next signal dies."""
    blocked = _run(60, 120, [10, 12], max_open=1, stop_at=11)
    open_ = _run(60, 0, [10, 12], max_open=1, stop_at=11)
    assert blocked.trades == 1
    assert open_.trades == 2


def test_m5_one_hundred_twenty_seconds_is_zero_bars():
    """The live wait is real and shorter than the bar, so paper does not bind."""
    stacked = _run(300, 120, [10, 20], max_open=2)
    sequential = _run(300, 120, [10, 12], max_open=1, stop_at=11)
    assert stacked.trades == 2
    assert sequential.trades == 2
