"""Night-hour gate is entry-only. Shrinking the session window is not the same.

Found in BP: live deals in broker hours 01/04/05/22 were −480$ of −612$
(45 days). The holdout test has to close those hours without force-closing
a position that is already open. ``session_windows`` plus
``flat_before_close_min`` would flatten at the new edge; this field must not.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.models import SymbolConfig
from micofx.sessions import evaluate, should_flatten
from micofx.strategy import IndicatorCache, Params, Signals

# Monday 1970-01-05. Bar times are naive broker-wall seconds, same as session_mask.
MON = 5 * 86400


def _cfg(**kwargs) -> SymbolConfig:
    cfg = SymbolConfig(
        symbol="NAS100",
        sessions=[{"start": "00:00", "end": "23:59"}],
        trade_days=[1, 2, 3, 4, 5],
        use_sessions=True,
        flat_before_close_min=5,
    )
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    return cfg


def test_hour_4_is_not_tradable_and_is_not_a_flatten():
    cfg = _cfg(blocked_entry_hours=[4])
    t = np.array([MON + 4 * 3600, MON + 12 * 3600])
    tradable = backtest.session_mask(cfg, t)
    flatten = backtest.flatten_mask(cfg, t)
    assert not tradable[0]
    assert tradable[1]
    assert not flatten[0]
    assert not flatten[1]


def test_shrinking_the_window_with_flat_before_does_flatten():
    """The alternative the brief forbids: rewrite the window, inherit flatten."""
    cfg = _cfg(sessions=[{"start": "00:00", "end": "04:00"}],
               blocked_entry_hours=[], flat_before_close_min=5)
    t = np.array([MON + 3 * 3600 + 55 * 60])
    assert bool(backtest.flatten_mask(cfg, t)[0])


def test_live_evaluate_blocks_the_hour_without_flatten():
    cfg = _cfg(blocked_entry_hours=[4])
    import calendar
    epoch = calendar.timegm((2026, 8, 17, 4, 0, 0, 0, 0, 0))  # Monday 04:00 broker
    state = evaluate(cfg, float(epoch))
    assert state.open is False
    assert state.reason == "saat kapali"
    assert should_flatten(cfg, float(epoch)) is False


def _sim(blocked, signal_hour: int):
    n = 80
    high = np.full(n, 100.0)
    low = np.full(n, 99.2)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    # Hourly bars starting Monday 00:00 so index == hour on day 1.
    times = MON + np.arange(n) * 3600
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[signal_hour] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=times, tf_seconds=3600,
                           open_=open_, volume=np.ones(n))
    cfg = _cfg(blocked_entry_hours=blocked, flat_before_close_min=5)
    tradable = backtest.session_mask(cfg, times)
    flatten = backtest.flatten_mask(cfg, times)
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0, cooldown_sec=0)
    return backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                             entries=np.array([signal_hour]),
                             tradable=tradable, flatten=flatten, min_stop=1.0)


def test_a_fill_before_the_blocked_hour_is_not_force_closed():
    """Signal at 02:00 fills 03:00; hour 04 is blocked for entry, not flatten."""
    res = _sim([4], 2)
    assert res.trades == 1
    assert res.exits.get("flatten", 0) == 0


def test_a_signal_that_would_fill_in_the_blocked_hour_is_skipped():
    """Signal at 03:00 would fill at 04:00 open — that bar is not tradable."""
    res = _sim([4], 3)
    assert res.trades == 0
