"""walk_forward must not re-impute spreads inside every simulate() call.

The series is constant for a search. walk_forward already runs
``imputed_spread_pts(bars.spread)`` once (AV1). simulate() used to do it
again per window/combo (~6.9 ms at 90k bars). Hoist ``trigger_pad`` the
same way ``spread_price`` is already hoisted.

Trap: the walk_forward ``spread_pts`` is already imputed. Building the
pad from that series must not call ``imputed_spread_pts`` a second time.
``spread_price`` may be scaled or zeroed when costs are off; the pad is a
stop trigger, not a cost — it stays raw-imputed × point.
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


def test_simulate_accepts_a_precomputed_trigger_pad():
    sig = inspect.signature(backtest.simulate)
    assert "trigger_pad" in sig.parameters
    assert sig.parameters["trigger_pad"].default is None


def test_walk_forward_passes_the_pad_and_imputes_once():
    src = inspect.getsource(backtest.walk_forward)
    assert "trigger_pad=" in src
    assert "spread_cost_series(" in src
    assert src.count("imputed_spread_pts(") == 0


def test_holdout_replay_passes_the_pad_without_reimputing():
    from micofx import holdout_cost
    src = inspect.getsource(holdout_cost.charged_holdout)
    assert "trigger_pad=" in src
    assert "imputed_spread_pts(spread_pts)" not in src


def _path():
    close = np.linspace(100.0, 110.0, N)
    close[ENTRY_BAR + 40:] = np.linspace(close[ENTRY_BAR + 39], 90.0,
                                         N - (ENTRY_BAR + 40))
    open_ = np.empty(N)
    open_[0] = close[0]
    open_[1:] = close[:-1]
    high = close + 0.4
    low = close - 0.4
    open_ = np.clip(open_, low, high)
    spread = np.full(N, 2.0)
    spread[:20] = 0.0
    buy = np.zeros(N, dtype=bool)
    buy[ENTRY_BAR] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(N, 1.0), adx=np.zeros(N),
                  buy=buy, sell=np.zeros(N, dtype=bool),
                  htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(N) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(N))
    return cache, sig, open_, spread


def test_passing_the_pad_matches_the_internal_impute():
    cache, sig, open_, spread = _path()
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.5, trail_step_atr=1.6)
    raw = backtest.simulate(cache, sig, open_, spread, point=0.01, p=p,
                            entries=np.array([ENTRY_BAR]))
    imputed = backtest.imputed_spread_pts(spread)
    pad = (imputed * 0.01).tolist()
    hoisted = backtest.simulate(cache, sig, open_, spread, point=0.01, p=p,
                                entries=np.array([ENTRY_BAR]),
                                trigger_pad=pad)
    assert raw.trades == hoisted.trades == 1
    assert raw.trade_rs == pytest.approx(hoisted.trade_rs)


@pytest.mark.parametrize("spread", [
    np.concatenate([np.zeros(400), np.full(1600, 2.0)]),
    np.concatenate([np.zeros(476), np.full(1524, 3.0)]),
    np.full(2000, 2.0),
    np.zeros(2000),
    np.concatenate([np.zeros(1999), np.array([2.0])]),
])
def test_a_second_impute_does_not_change_the_pad(spread):
    """Claude 25.08: walk_forward already imputed; a second pass is identity.

    The hoist ``spread_pts * point`` equals simulate()'s None fallback
    ``imputed(spread_pts) * point`` only because imputed_spread_pts is
    idempotent. All-zero and single-quote are the two branches.
    """
    once = backtest.imputed_spread_pts(spread)
    twice = backtest.imputed_spread_pts(once)
    assert np.array_equal(once, twice)
    point = 0.1
    hoisted = once * point
    inside = twice * point
    assert np.array_equal(hoisted, inside)


def test_sig_cache_evicts_the_oldest_key_not_the_whole_map():
    from collections import OrderedDict

    cache = OrderedDict()
    for i in range(4):
        backtest._store_sig_cache(cache, i, i)
    backtest._store_sig_cache(cache, 4, 4)
    assert list(cache) == [1, 2, 3, 4]
    backtest._store_sig_cache(cache, 2, "hit")
    backtest._store_sig_cache(cache, 5, 5)
    assert list(cache.keys()) == [3, 4, 2, 5]
    assert cache[2] == "hit"
