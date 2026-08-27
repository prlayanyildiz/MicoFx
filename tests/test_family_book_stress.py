"""Hostile bars must not crash a family, leak a both-sides bar, or revive a dead name.

80-row opt history (26.08): every remaining family that posted a holdout
was PF>=1.10 and net R>0. That is not the mavilim bar (GER -20 R / PF 0.92)
and not alpha_trend's 7 trades. Live book uses stoch_flip, burst,
mtf_pullback, parabolic_flip - deleting a family that is merely 'rarely
applied' shrinks the next search's optionality. This file pins the
invariants instead: 11 names, fail-closed leftovers, compute under junk
tape, harvest overlay never loosens a stop.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.exits import overlay_stop
from micofx.models import STRATEGIES
from micofx.strategy import (
    _FAMILIES,
    _UNKNOWN_FAMILIES,
    IndicatorCache,
    Params,
    _resolve_conflicts,
    compute,
)

LIVE_NOW = ("stoch_flip", "burst", "mtf_pullback", "parabolic_flip")
RETIRED = ("alpha_trend", "mavilim", "trix_flip", "flow_rev",
           "orb_retest", "t3_ribbon", "st_trend", "macd_flip")


def _cache(close: np.ndarray, *, cost: float | None = 0.05) -> IndicatorCache:
    close = np.asarray(close, dtype=np.float64)
    n = close.size
    high = close + np.maximum(0.05, np.abs(close) * 0.001)
    low = close - np.maximum(0.05, np.abs(close) * 0.001)
    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1]
    open_ = np.clip(open_, low, high)
    cost_arr = None if cost is None else np.full(n, float(cost))
    return IndicatorCache(
        high=high, low=low, close=close, open_=open_,
        times=np.arange(n, dtype=np.int64) * 300, tf_seconds=300,
        volume=np.ones(n), cost=cost_arr,
    )


def _shapes(n: int = 420):
    rng = np.random.default_rng(26_08_26)
    flat = np.full(n, 100.0)
    up = 100 + np.linspace(0, 40, n)
    down = 100 - np.linspace(0, 40, n)
    walk = 100 + np.cumsum(rng.normal(0, 0.6, n))
    gappy = walk.copy()
    gappy[n // 2] += 25.0
    gappy[n // 2 + 1] -= 18.0
    short = 50 + np.cumsum(rng.normal(0, 0.3, 90))
    return {
        "flat": flat,
        "up": up,
        "down": down,
        "walk": walk,
        "gappy": gappy,
        "short": short,
    }


@pytest.mark.parametrize("name", STRATEGIES)
@pytest.mark.parametrize("shape", ["flat", "up", "down", "walk", "gappy", "short"])
def test_every_family_survives_hostile_tape(name, shape):
    cache = _cache(_shapes()[shape])
    sig = compute(cache, Params(strategy=name))
    assert sig.buy.shape == cache.close.shape
    assert sig.sell.shape == cache.close.shape
    assert not np.any(sig.buy & sig.sell), f"{name}/{shape} buy AND sell"
    assert np.isfinite(sig.atr).all()
    assert not np.any(np.isnan(sig.buy.astype(np.float64)))


def test_scalps_without_cost_stay_flat_not_crash():
    cache = _cache(_shapes()["walk"], cost=None)
    for name in ("burst",):
        sig = compute(cache, Params(strategy=name))
        assert not sig.buy.any() and not sig.sell.any()


@pytest.fixture(autouse=True)
def _forget_unknown():
    _UNKNOWN_FAMILIES.clear()
    yield
    _UNKNOWN_FAMILIES.clear()


@pytest.mark.parametrize("name", RETIRED)
def test_retired_names_fail_closed(name):
    assert name not in STRATEGIES
    assert name not in _FAMILIES
    sig = compute(_cache(_shapes()["walk"]), Params(strategy=name))
    assert not sig.buy.any() and not sig.sell.any()


def test_live_book_families_are_still_searchable():
    for name in LIVE_NOW:
        assert name in STRATEGIES
        assert name in _FAMILIES
    assert len(STRATEGIES) == 8
    assert set(STRATEGIES) == set(_FAMILIES)


def test_harvest_off_matches_omitted_kwargs():
    kw = {
        "is_buy": True, "entry": 100.0, "ref": 103.0, "atr": 1.0,
        "trail_start_atr": 0.5, "trail_step_atr": 1.8, "trail_mode": "atr",
        "struct_sl": None, "breakeven_at_r": 1.5, "original_risk": 1.0,
    }
    assert overlay_stop(**kw) == overlay_stop(**kw, harvest_at_r=0.0,
                                              harvest_step_atr=0.4)


def test_every_builder_drops_a_both_sides_bar():
    for name, fn in _FAMILIES.items():
        assert "_resolve_conflicts" in inspect.getsource(fn), name


def test_resolve_conflicts_zeros_both_sides():
    buy = np.array([True, True, False, True])
    sell = np.array([True, False, True, True])
    b, s = _resolve_conflicts(buy, sell)
    assert not np.any(b & s)
    assert b.tolist() == [False, True, False, False]
    assert s.tolist() == [False, False, True, False]


@pytest.mark.parametrize("name", STRATEGIES)
def test_doji_inverted_tiny_huge_and_nan_do_not_crash(name):
    n = 120
    close = 100 + np.cumsum(np.random.default_rng(3).normal(0, 0.4, n))
    cases = []
    doji = IndicatorCache(
        high=close.copy(), low=close.copy(), close=close, open_=close,
        times=np.arange(n, dtype=np.int64) * 300, tf_seconds=300,
        volume=np.ones(n), cost=np.full(n, 0.05))
    cases.append(doji)
    inv = IndicatorCache(
        high=close - 1.0, low=close + 1.0, close=close, open_=close,
        times=np.arange(n, dtype=np.int64) * 300, tf_seconds=300,
        volume=np.ones(n), cost=np.full(n, 0.05))
    cases.append(inv)
    cases.append(_cache(np.full(8, 100.0)))
    cases.append(_cache(4000 + np.cumsum(np.random.default_rng(4).normal(0, 8, 300))))
    nan_c = close.copy()
    nan_c[40] = np.nan
    cases.append(_cache(nan_c))
    for cache in cases:
        sig = compute(cache, Params(strategy=name))
        assert sig.buy.shape == cache.close.shape
        assert not np.any(sig.buy & sig.sell), name


@pytest.mark.parametrize("name", STRATEGIES)
def test_paper_replay_survives_every_family(name):
    cache = _cache(_shapes()["walk"])
    sig = compute(cache, Params(strategy=name))
    res = backtest.simulate(
        cache, sig, cache.open, np.zeros(cache.close.size), point=0.01,
        p=Params(strategy=name, sl_atr_mult=1.2, trail_start_atr=0.8,
                 trail_step_atr=1.6, harvest_at_r=1.5, harvest_step_atr=0.4))
    assert np.isfinite(res.net_r)
    assert np.isfinite(res.max_dd_r)
    assert res.trades >= 0
    off = backtest.simulate(
        cache, sig, cache.open, np.zeros(cache.close.size), point=0.01,
        p=Params(strategy=name, sl_atr_mult=1.2, trail_start_atr=0.8,
                 trail_step_atr=1.6))
    on = backtest.simulate(
        cache, sig, cache.open, np.zeros(cache.close.size), point=0.01,
        p=Params(strategy=name, sl_atr_mult=1.2, trail_start_atr=0.8,
                 trail_step_atr=1.6, harvest_at_r=0.0, harvest_step_atr=0.4))
    assert off.trade_rs == on.trade_rs


@pytest.mark.parametrize("is_buy", [True, False])
def test_harvest_never_loosens_the_stop(is_buy):
    rng = np.random.default_rng(15)
    for ref in rng.uniform(97.0, 108.0, 80):
        kw = {
            "is_buy": is_buy, "entry": 100.0, "ref": float(ref), "atr": 1.0,
            "trail_start_atr": 1.0, "trail_step_atr": 1.8, "trail_mode": "atr",
            "struct_sl": None, "breakeven_at_r": 1.5, "original_risk": 1.0,
        }
        off = overlay_stop(**kw)
        on = overlay_stop(**kw, harvest_at_r=1.5, harvest_step_atr=0.4)
        if on is None:
            assert off is None
            continue
        if off is None:
            continue
        if is_buy:
            assert on >= off - 1e-12
        else:
            assert on <= off + 1e-12
