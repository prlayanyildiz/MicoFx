"""Parity with live cooldown breaks when the pause is shorter than a bar.

Live waits ``cooldown_sec`` wall-clock seconds after a fill, capped at one
or two bars of the TF (``engine._cooldown_for``). Paper turns the same cap
into ``capped // tf_seconds`` bars.

On this book every symbol is 120s and every TF is 300s or more, so paper
gets 0 bars and a search never feels the wait. Live still waits 120s; the
next bar arrives after that, so the two agree by accident.

The split is not "M1" and it is not "the sequential arm has no cooldown".
It is ``cooldown_sec >= tf_seconds``:

* below the threshold, both paper arms are a no-op (today's book).
* at one bar, the stacked arm drops the next signal; the sequential arm
  still takes it after a same-bar stop, because its remainder is
  ``j0 + 1 - 1 = j0`` and the next signal bar is later than that.
* at two bars, the sequential remainder also drops the next signal.

Live's second count is always in seconds and is tested here only as the
pure ``_cooldown_for`` number - the engine loop is the other side of the
bridge.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.engine import _cooldown_for
from micofx.models import SymbolConfig
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


def test_below_a_bar_paper_is_a_noop_and_live_still_waits():
    """Today's book: 120s on M5. Paper 0 bars; live `_cooldown_for` is 120."""
    assert _cooldown_for(SymbolConfig(
        symbol="JPN225", timeframe="M5", cooldown_sec=120,
        strategy="dual_t3")) == 120.0
    stacked = _run(300, 120, [10, 11], max_open=2)
    sequential = _run(300, 120, [10, 12], max_open=1, stop_at=11)
    assert stacked.trades == 2
    assert sequential.trades == 2


def test_at_one_bar_the_stacked_arm_drops_the_next_signal():
    """M5 at 300s is the threshold. Fill at 11 cools signal bar 11, not 12."""
    assert _run(300, 300, [10, 11], max_open=2).trades == 1
    assert _run(300, 300, [10, 12], max_open=2).trades == 2
    assert _run(300, 0, [10, 11], max_open=2).trades == 2


def test_at_one_bar_the_sequential_arm_still_takes_the_next_signal():
    """Same-bar stop: remainder lands on the fill bar, so signal 12 survives."""
    assert _run(300, 300, [10, 12], max_open=1, stop_at=11).trades == 2


def test_at_two_bars_the_sequential_remainder_also_drops_it():
    assert _run(300, 600, [10, 12], max_open=1, stop_at=11).trades == 1
    assert _run(300, 0, [10, 12], max_open=1, stop_at=11).trades == 2
