"""Minimal regression net over the pieces most likely to silently break:
session gating, the SL/TP bar-replay, live lot sizing, MT5 deal merging, and
the optimizer's apply gate. Not exhaustive - a starting net, not full coverage.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.models import SymbolConfig, SystemConfig
from micofx.mt5client import MT5Client
from micofx.optimizer import Optimizer
from micofx.risk import DailyGuard, RiskManager

# --------------------------------------------------------------------------- session_mask

def test_session_mask_inside_window_allowed():
    cfg = SymbolConfig(symbol="EURUSD", sessions=[{"start": "08:00", "end": "17:00"}],
                        trade_days=[1, 2, 3, 4, 5])
    # 1970-01-05 is a Monday; 12:00 that day is well inside the window.
    t = np.array([5 * 86400 + 12 * 3600])
    assert backtest.session_mask(cfg, t)[0]


def test_session_mask_outside_window_blocked():
    cfg = SymbolConfig(symbol="EURUSD", sessions=[{"start": "08:00", "end": "17:00"}],
                        trade_days=[1, 2, 3, 4, 5])
    t = np.array([5 * 86400 + 20 * 3600])  # 20:00 Monday, outside 08-17
    assert not backtest.session_mask(cfg, t)[0]


def test_session_mask_weekend_blocked_on_trade_days():
    cfg = SymbolConfig(symbol="EURUSD", sessions=[{"start": "00:00", "end": "23:59"}],
                        trade_days=[1, 2, 3, 4, 5])
    t = np.array([3 * 86400 + 12 * 3600])  # 1970-01-03 is a Saturday
    assert not backtest.session_mask(cfg, t)[0]


def test_session_mask_all_hours_override_keeps_weekday():
    cfg = SymbolConfig(symbol="EURUSD", sessions=[{"start": "08:00", "end": "09:00"}],
                        trade_days=[1, 2, 3, 4, 5])
    t = np.array([5 * 86400 + 20 * 3600])  # Monday 20:00, outside the narrow window
    assert backtest.session_mask(cfg, t, all_hours=True)[0]


# --------------------------------------------------------------------------- bar replay SL/TP

def _flat_bars(n=200, price=100.0):
    return (np.full(n, price), np.full(n, price), np.full(n, price), np.full(n, price))


def test_simulate_stops_out_a_long_on_the_stop_leg():
    n = 60
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    # Entry bar signal at i=10; fills at open of bar 11 (~100); the very next
    # bar's low wicks down through any reasonable ATR-based stop.
    low[12] = 90.0
    close[12] = 95.0

    from micofx.strategy import IndicatorCache, Params, Signals
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    sell = np.zeros(n, dtype=bool)
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=sell, htf_up=np.zeros(n, dtype=bool),
                  htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0)
    res = backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                            entries=np.array([10]))
    assert res.trades == 1
    assert res.losses == 1
    assert res.trade_rs[0] < 0


def test_simulate_skips_entry_with_nan_atr():
    # M5: mirrors engine._try_entry's live ATR gate - a bare ``atr <= 0``
    # check is not fail-closed for NaN (NaN compares False to everything), so
    # a NaN'd entry-bar ATR must not size sl_dist/tp_dist and produce a
    # corrupt R value.
    n = 60
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    low[12] = 90.0
    close[12] = 95.0

    from micofx.strategy import IndicatorCache, Params, Signals
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    sell = np.zeros(n, dtype=bool)
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=sell, htf_up=np.zeros(n, dtype=bool),
                  htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0)
    # Corrupt just the entry bar's cached ATR value directly - simulate()
    # reads cache.atr_list(p.atr_period), not sig.atr.
    corrupted = cache.atr_list(p.atr_period)
    corrupted[10] = float("nan")
    cache._atr_lists[p.atr_period] = corrupted

    res = backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                            entries=np.array([10]))
    assert res.trades == 0


def test_simulate_exits_a_long_on_the_trail_not_a_target():
    n = 60
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    high[12] = 110.0
    close[12] = 105.0
    # Bar 13 opens at the previous close (no gap) and wicks through the trail.
    # Opening at 100 would be a gap through the trailed SL and fill at open.
    open_[13] = 105.0
    high[13] = 105.0
    low[13] = 100.0
    close[13] = 100.0

    from micofx.strategy import IndicatorCache, Params, Signals
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    sell = np.zeros(n, dtype=bool)
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=sell, htf_up=np.zeros(n, dtype=bool),
                  htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    # Bar 12 runs 5 ATR into profit and closes at 105, so the trail arms and
    # ratchets the stop to 104.5. Bar 13 opens at that close and wicks to 100,
    # filling the trail at 104.5. A spike to 110 must not close anything by
    # itself — there is no take-profit level in this system.
    p = Params(sl_atr_mult=1.0, trail_start_atr=1.0, trail_step_atr=0.5)
    res = backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                            entries=np.array([10]))
    assert res.trades == 1
    assert res.wins == 1
    assert res.trade_rs[0] > 0
    assert res.exits.get("trail") == 1
    assert "target" not in res.exits


def test_simulate_never_produces_a_target_exit():
    """No configuration can put a take-profit back into the simulator.

    A long that spikes far beyond any old tp_atr_mult and then comes all the
    way back must ride the trail down, not book a fixed target on the spike.
    """
    n = 80
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    high[12] = 140.0            # far past any target the old grid could set
    close[12] = 101.0           # ...but closes back at +1
    low[20] = 90.0              # later gives it all back

    from micofx.strategy import IndicatorCache, Params, Signals
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    res = backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01,
                            p=Params(sl_atr_mult=1.0, trail_start_atr=0.5,
                                     trail_step_atr=0.5),
                            entries=np.array([10]))
    assert res.trades == 1
    assert "target" not in res.exits
    assert set(res.exits) <= {"stop", "trail", "flatten", "time"}


def test_simulate_has_no_time_stop():
    """A quiet trade stays open to the end of the sample, not to a bar count.

    Nothing here ever reaches the stop or the trail, so the only way this can
    end is the sample running out. If a time stop existed the exit reason would
    still be "time", but it would land far earlier - so the hold length is what
    actually distinguishes the two.
    """
    n = 400
    high = np.full(n, 100.2)
    low = np.full(n, 99.8)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)

    from micofx.strategy import IndicatorCache, Params, Signals
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300, tf_seconds=300,
                           open_=open_, volume=np.ones(n))
    res = backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01,
                            p=Params(sl_atr_mult=2.0, trail_start_atr=5.0),
                            entries=np.array([10]))
    assert res.trades == 1
    # Held to the last bar of the sample (~389 bars), nowhere near the 12-96
    # bar caps the old max_bars_in_trade grid used to impose.
    assert res.avg_bars > 300


# --------------------------------------------------------------------------- lot_for / ai_scale

class _FakeSystem:
    lot_multiplier = 1.0
    size_by_edge = False
    max_positions = 1
    max_lot = 0.0


class _FakeStore:
    system = _FakeSystem()
    symbols: dict = {}

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass


class _FakeClient:
    """Just enough of MT5Client's surface for RiskManager.lot_for."""

    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 100.0, "volume_step": 0.1}

    def money_per_price_unit(self, symbol, lot):
        return 10.0

    def min_stop_distance(self, symbol):
        return 0.0

    def normalize_volume(self, symbol, lot):
        step = 0.1
        return round(round(lot / step) * step, 2)

    def resolve(self, symbol):
        return symbol

    def margin_for(self, symbol, lot, side):
        return 1.0


def _cfg(**over):
    base = {"symbol": "TEST", "lot_mode": "risk", "risk_percent": 1.0, "max_lot": 0.3}
    base.update(over)
    return SymbolConfig(**base)


def test_lot_for_ai_scale_shrinks_lot_before_floor_when_room_allows():
    risk = RiskManager(_FakeStore(), _FakeClient())
    # 1000 * 1% / (1.0 * 10) = 1.0 lot; 0.3 scale has room above the 0.1 floor.
    cfg = _cfg(risk_percent=1.0)
    lot, note = risk.lot_for(cfg, sl_distance=1.0, balance=1000.0, ai_scale=0.3)
    assert lot == pytest.approx(0.3, abs=0.01)


def test_lot_for_ai_scale_skips_trade_past_overshoot_guard():
    risk = RiskManager(_FakeStore(), _FakeClient())
    # 0.1% of 1000 / 10 = 0.1 lot * 0.05 scale = 0.005 vs 0.1 floor → 20x skip
    cfg = _cfg(risk_percent=0.1)
    lot, note = risk.lot_for(cfg, sl_distance=1.0, balance=1000.0, ai_scale=0.05)
    assert lot == 0.0
    assert "atlandi" in note


def test_lot_for_ai_scale_within_overshoot_forces_floor():
    risk = RiskManager(_FakeStore(), _FakeClient())
    cfg = _cfg(risk_percent=0.1)
    # floor/r_cap = 0.1/0.066... ≈ 1.5 → at the 1.5x ceiling, force floor
    lot, note = risk.lot_for(cfg, sl_distance=1.0, balance=1000.0, ai_scale=0.67)
    assert lot == pytest.approx(0.1)


def test_lot_for_overshoot_guard_uses_tightened_1_5x_ceiling():
    # T1: 3.0x → 1.5x. An overshoot the old ceiling tolerated (~2x) must skip.
    risk = RiskManager(_FakeStore(), _FakeClient())
    cfg = _cfg(risk_percent=0.1)
    lot, note = risk.lot_for(cfg, sl_distance=1.0, balance=1000.0, ai_scale=0.5)  # 2x
    assert lot == 0.0
    assert "atlandi" in note


def test_lot_for_risk_mode_fails_closed_without_tick_value():
    # A missing/zero tick value used to fall back to fixed_lot, silently
    # skipping max_lot, edge/AI scaling and the overshoot guard entirely -
    # must refuse the trade instead.
    class _NoTickClient(_FakeClient):
        def money_per_price_unit(self, symbol, lot):
            return 0.0

    risk = RiskManager(_FakeStore(), _NoTickClient())
    cfg = _cfg(lot_mode="risk", risk_percent=0.5)
    lot, note = risk.lot_for(cfg, sl_distance=1.0, balance=1000.0)
    assert lot == 0.0
    assert "tick" in note


# --------------------------------------------------------------------------- can_open / position counts

def test_can_open_symbol_limit_is_one_ticket():
    """Leftover max_positions unread. A second same-side ticket is refused."""
    store = _FakeStore()
    store.system = _FakeSystem()
    cfg = _cfg(symbol="XAUUSD", magic=1, strategy="stoch_flip", max_positions=1)
    store.symbols = {"XAUUSD": cfg}
    store.system.max_scalp_positions = 10
    store.system.max_swing_positions = 10
    store.system.max_total_positions = 10
    store.system.min_free_margin = 0.0
    store.system.max_margin_usage_pct = 0.0

    risk = RiskManager(store, _FakeClient())
    existing = [{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}

    blocked = risk.can_open(cfg, "buy", 0.1, existing, account)
    assert not blocked.ok
    assert "sembol pozisyon limiti" in blocked.reason


def test_can_open_bucket_uses_primary_strategy_only():
    """A leftover tagged ticket counts as the stored primary family.

    The old sec_tickets path re-bucketed it as secondary_strategy (scalp).
    """
    store = _FakeStore()
    store.system = _FakeSystem()
    primary = _cfg(symbol="XAUUSD", magic=1, strategy="stoch_flip", max_positions=5)
    ger = _cfg(symbol="GER40", magic=2, strategy="burst", max_positions=5)
    nas = _cfg(symbol="NAS100", magic=3, strategy="stoch_flip", max_positions=5)
    store.symbols = {"XAUUSD": primary, "GER40": ger, "NAS100": nas}
    store.system.max_scalp_positions = 1
    store.system.max_swing_positions = 1
    store.system.max_total_positions = 10
    store.system.min_free_margin = 0.0
    store.system.max_margin_usage_pct = 0.0

    risk = RiskManager(store, _FakeClient())
    existing = [{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}

    scalp_cfg = _cfg(symbol="GER40", magic=2, strategy="burst", max_positions=5)
    scalp = risk.can_open(scalp_cfg, "buy", 0.1, existing, account)
    assert scalp.ok  # leftover sits in the swing bucket now

    swing_cfg = _cfg(symbol="NAS100", magic=3, strategy="stoch_flip", max_positions=5)
    swing = risk.can_open(swing_cfg, "buy", 0.1, existing, account)
    assert not swing.ok
    assert "swing" in swing.reason


def test_can_open_allows_when_bucket_not_full():
    store = _FakeStore()
    primary = _cfg(symbol="XAUUSD", magic=1, strategy="stoch_flip", max_positions=5)
    ger = _cfg(symbol="GER40", magic=2, strategy="burst", max_positions=5)
    store.symbols = {"XAUUSD": primary, "GER40": ger}
    store.system.max_scalp_positions = 2
    store.system.max_swing_positions = 5
    store.system.max_total_positions = 10
    store.system.min_free_margin = 0.0
    store.system.max_margin_usage_pct = 0.0

    risk = RiskManager(store, _FakeClient())
    existing = [{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}

    new_cfg = _cfg(symbol="GER40", magic=2, strategy="burst", max_positions=5)
    verdict = risk.can_open(new_cfg, "buy", 0.1, existing, account)
    assert verdict.ok


# --------------------------------------------------------------------------- merge_round_trips

import MetaTrader5 as mt5  # noqa: E402  (installed on this machine - see mt5client.py)


def test_merge_round_trips_sums_partial_fills_into_one_trade():
    deals = [
        {"position": 1, "symbol": "EURUSD", "magic": 1, "time": 100,
         "profit": 5.0, "commission": -0.5, "swap": 0.0, "entry": mt5.DEAL_ENTRY_OUT},
        {"position": 1, "symbol": "EURUSD", "magic": 1, "time": 110,
         "profit": -1.0, "commission": -0.5, "swap": 0.0, "entry": mt5.DEAL_ENTRY_OUT},
        {"position": 2, "symbol": "EURUSD", "magic": 1, "time": 105,
         "profit": -3.0, "commission": -0.5, "swap": 0.0, "entry": mt5.DEAL_ENTRY_OUT},
    ]
    merged = MT5Client.merge_round_trips(deals)
    assert len(merged) == 2
    by_pos = {r["position"]: r for r in merged}
    assert by_pos[1]["profit"] == pytest.approx(4.0)
    assert by_pos[1]["commission"] == pytest.approx(-1.0)
    assert by_pos[1]["time"] == 110  # timestamped at the LAST (closing) fill
    # sorted by time ascending: position 2 (t=105) before position 1 (t=110)
    assert [r["position"] for r in merged] == [2, 1]


def test_merge_round_trips_folds_in_entry_side_commission():
    # M4: DEAL_ENTRY_IN now carries commission too (some brokers split the
    # round-turn commission across both legs) - a closed position's IN deal
    # must be folded into the total, not silently dropped.
    deals = [
        {"position": 1, "symbol": "EURUSD", "magic": 1, "time": 100,
         "profit": 0.0, "commission": -0.4, "swap": 0.0, "entry": mt5.DEAL_ENTRY_IN},
        {"position": 1, "symbol": "EURUSD", "magic": 1, "time": 110,
         "profit": 5.0, "commission": -0.4, "swap": 0.0, "entry": mt5.DEAL_ENTRY_OUT},
    ]
    merged = MT5Client.merge_round_trips(deals)
    assert len(merged) == 1
    assert merged[0]["commission"] == pytest.approx(-0.8)  # both legs, not just the OUT one
    assert merged[0]["profit"] == pytest.approx(5.0)


def test_merge_round_trips_excludes_still_open_position():
    # A position with only an IN deal (no OUT/INOUT/OUT_BY yet) hasn't
    # actually closed - it must not be reported as a zero-profit "trade".
    deals = [
        {"position": 1, "symbol": "EURUSD", "magic": 1, "time": 100,
         "profit": 0.0, "commission": -0.4, "swap": 0.0, "entry": mt5.DEAL_ENTRY_IN},
    ]
    merged = MT5Client.merge_round_trips(deals)
    assert merged == []


# --------------------------------------------------------------------------- optimizer.reject_reason

def _result(net_r=10.0, trades=30, pf=1.5, cost_per_trade_r=0.05, score=5.0,
            expectancy=None):
    # ``expectancy`` is net_r/trades in the real Result summary (see
    # backtest.Result.expectancy). Leaving it off made these doubles claim a
    # candidate that nets +10R over 30 trades while earning 0.0 per trade -
    # incoherent, and invisible until a gate started reading it.
    return {
        "trades": trades, "net_r": net_r, "profit_factor": pf,
        "cost_per_trade_r": cost_per_trade_r, "score": score,
        "expectancy": (net_r / trades if trades else 0.0)
        if expectancy is None else expectancy,
    }


def test_reject_reason_accepts_a_clean_candidate_with_no_incumbent():
    opt = Optimizer(store=None, client=None)
    best = {
        "holdout": _result(), "validation": _result(),
        "positive_ratio": 1.0, "score": 5.0,
    }
    assert opt.reject_reason(None, best) == ""


def test_reject_reason_flags_unprofitable_holdout():
    opt = Optimizer(store=None, client=None)
    best = {
        "holdout": _result(net_r=-5.0, pf=0.7), "validation": _result(),
        "positive_ratio": 1.0, "score": 5.0,
    }
    reason = opt.reject_reason(None, best)
    assert "dokunulmamis test" in reason


def test_reject_reason_flags_high_cost():
    opt = Optimizer(store=None, client=None)
    best = {
        "holdout": _result(cost_per_trade_r=opt.MAX_COST_PER_TRADE_R + 0.5),
        "validation": _result(), "positive_ratio": 1.0, "score": 5.0,
    }
    assert opt.reject_reason(None, best) == "islem maliyeti riske gore cok yuksek"


class _MinPositiveStore:
    """Just enough of Store for reject_reason()'s min_positive_ratio read."""
    def __init__(self, min_positive_ratio):
        self._params = {"min_positive_ratio": min_positive_ratio}

    def opt_params(self):
        return self._params


def test_reject_reason_uses_hardcoded_default_when_no_store():
    # store=None (e.g. a unit test double, or before Optimizer is wired up)
    # must not crash - falls back to the same 0.6 the setting itself defaults
    # to.
    opt = Optimizer(store=None, client=None)
    best = {
        "holdout": _result(), "validation": _result(),
        "positive_ratio": 0.5, "score": 5.0,
    }
    assert opt.reject_reason(None, best) == "secim segmentleri arasinda tutarsiz"


def test_reject_reason_honours_configured_min_positive_ratio_below_default():
    # Regression pin: reject_reason() used to hardcode 0.6 regardless of the
    # user-configured min_positive_ratio (UI allows down to 0.3, and
    # backtest.py's own walk_forward search already honours the configured
    # value) - a candidate the search validated at e.g. 0.5 consistency was
    # silently re-rejected here anyway under a threshold nobody set.
    opt = Optimizer(store=_MinPositiveStore(0.4), client=None)
    best = {
        "holdout": _result(), "validation": _result(),
        "positive_ratio": 0.5, "score": 5.0,
    }
    assert opt.reject_reason(None, best) == ""


def test_reject_reason_still_rejects_below_configured_lower_threshold():
    opt = Optimizer(store=_MinPositiveStore(0.4), client=None)
    best = {
        "holdout": _result(), "validation": _result(),
        "positive_ratio": 0.35, "score": 5.0,
    }
    assert opt.reject_reason(None, best) == "secim segmentleri arasinda tutarsiz"


def test_reject_reason_honours_configured_min_positive_ratio_above_default():
    opt = Optimizer(store=_MinPositiveStore(0.8), client=None)
    best = {
        "holdout": _result(), "validation": _result(),
        "positive_ratio": 0.7, "score": 5.0,  # would have passed the old hardcoded 0.6
    }
    assert opt.reject_reason(None, best) == "secim segmentleri arasinda tutarsiz"


# --------------------------------------------------------------------------- secondary pick removed (A1, 14.08)

def test_optimizer_no_longer_picks_or_writes_a_secondary():
    """Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok.

    These used to pin apply_secondary() identity-swap / orphan / disconnect
    guards. That writer is gone; the replacement pin is that the methods
    themselves are absent so a search cannot mint a new candidate.
    """
    assert not hasattr(Optimizer, "apply_secondary")
    assert not hasattr(Optimizer, "_pick_secondary")
    assert not hasattr(Optimizer, "_apply_secondary_locked")


# --------------------------------------------------------------------------- DailyGuard loss_halted

class _DailyStore:
    def __init__(self):
        self.system = SystemConfig(daily_loss_pct=3.0, daily_profit_pct=5.0)
        self._settings = {}

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key, value):
        self._settings[key] = value


def test_daily_guard_loss_breach_sets_sticky_loss_halted():
    store = _DailyStore()
    guard = DailyGuard(store)
    guard.start_balance = 1000.0

    guard.check(equity=960.0, sys_cfg=store.system)  # -4% breaches the 3% cap

    assert guard.halted is True
    assert guard.loss_halted is True


def test_daily_guard_profit_target_does_not_set_loss_halted():
    store = _DailyStore()
    guard = DailyGuard(store)
    guard.start_balance = 1000.0

    guard.check(equity=1060.0, sys_cfg=store.system)  # +6% hits the 5% profit target

    assert guard.halted is True
    assert guard.loss_halted is False


def test_daily_guard_loss_halted_survives_equity_bounce():
    # Once tripped, loss_halted must NOT flip back off just because equity
    # (or pnl_pct recomputed from it) improves mid-day - only rollover/resume
    # clears it. This is the sticky flag engine._cycle()'s flatten now reads
    # instead of re-deriving from live pnl_pct every cycle.
    store = _DailyStore()
    guard = DailyGuard(store)
    guard.start_balance = 1000.0
    guard.check(equity=960.0, sys_cfg=store.system)
    assert guard.loss_halted is True

    # Equity bounces back above the -3% line; check() short-circuits on
    # self.halted before even looking at pnl_pct again either way.
    guard.check(equity=995.0, sys_cfg=store.system)
    assert guard.halted is True
    assert guard.loss_halted is True


def test_daily_guard_rollover_clears_loss_halted():
    import time as _time
    store = _DailyStore()
    guard = DailyGuard(store)
    guard.start_balance = 1000.0
    guard.check(equity=960.0, sys_cfg=store.system)
    assert guard.loss_halted is True

    guard.rollover(server_epoch=_time.time() + 86400 * 2, balance=1000.0)

    assert guard.halted is False
    assert guard.loss_halted is False


def test_daily_guard_resume_clears_loss_halted():
    store = _DailyStore()
    guard = DailyGuard(store)
    guard.start_balance = 1000.0
    guard.check(equity=960.0, sys_cfg=store.system)
    assert guard.loss_halted is True

    guard.resume()

    assert guard.halted is False
    assert guard.loss_halted is False


