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
    p = Params(sl_atr_mult=1.0, tp_atr_mult=0.0, trail_start_atr=0.0)
    res = backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                            entries=np.array([10]))
    assert res.trades == 1
    assert res.losses == 1
    assert res.trade_rs[0] < 0


def test_simulate_targets_a_long_on_the_target_leg():
    n = 60
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    high[12] = 110.0
    close[12] = 105.0

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
    p = Params(sl_atr_mult=1.0, tp_atr_mult=1.0, trail_start_atr=0.0)
    res = backtest.simulate(cache, sig, open_, np.zeros(n), point=0.01, p=p,
                            entries=np.array([10]))
    assert res.trades == 1
    assert res.wins == 1
    assert res.trade_rs[0] > 0


# --------------------------------------------------------------------------- lot_for / ai_scale

class _FakeSystem:
    lot_multiplier = 1.0
    size_by_edge = False


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
    base = dict(symbol="TEST", lot_mode="fixed", fixed_lot=0.1, max_lot=0.3)
    base.update(over)
    return SymbolConfig(**base)


def test_lot_for_ai_scale_shrinks_lot_before_floor_when_room_allows():
    risk = RiskManager(_FakeStore(), _FakeClient())
    cfg = _cfg(fixed_lot=1.0)  # floor is 0.1, so a 0.3 scale has room to actually shrink
    lot, note = risk.lot_for(cfg, sl_distance=1.0, balance=1000.0, ai_scale=0.3)
    assert lot == pytest.approx(0.3, abs=0.01)


def test_lot_for_ai_scale_skips_trade_past_overshoot_guard():
    risk = RiskManager(_FakeStore(), _FakeClient())
    # fixed_lot * ai_scale lands far below the 0.1 floor - beyond the 3x
    # overshoot tolerance, so this should refuse rather than silently size up.
    cfg = _cfg(fixed_lot=0.1)
    lot, note = risk.lot_for(cfg, sl_distance=1.0, balance=1000.0, ai_scale=0.05)
    assert lot == 0.0
    assert "atlandi" in note


def test_lot_for_ai_scale_within_overshoot_forces_floor():
    risk = RiskManager(_FakeStore(), _FakeClient())
    cfg = _cfg(fixed_lot=0.1)
    lot, note = risk.lot_for(cfg, sl_distance=1.0, balance=1000.0, ai_scale=0.5)
    assert lot == pytest.approx(0.1)


def test_lot_for_overshoot_guard_uses_tightened_3x_ceiling():
    # Regression pin for the B1 tightening (10.0x -> 3.0x): an overshoot that
    # the old, looser ceiling would have tolerated (silently sizing a trade at
    # ~5x its configured risk) must now be refused instead.
    risk = RiskManager(_FakeStore(), _FakeClient())
    cfg = _cfg(fixed_lot=0.1)
    lot, note = risk.lot_for(cfg, sl_distance=1.0, balance=1000.0, ai_scale=0.2)  # 5x overshoot
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


# --------------------------------------------------------------------------- can_open / ensemble bucket

def test_can_open_counts_secondary_tagged_position_by_its_own_family():
    # Primary is swing (st_trend), secondary is scalp (micro_rev), sharing one
    # magic. One position is already open, opened off the SECONDARY signal.
    store = _FakeStore()
    store.system = _FakeSystem()  # fresh instance - do not mutate the shared class default
    primary = _cfg(symbol="XAUUSD", magic=1, strategy="st_trend",
                   secondary_strategy="micro_rev", max_positions=5)
    store.symbols = {"XAUUSD": primary}
    store.system.max_scalp_positions = 1
    store.system.max_swing_positions = 5
    store.system.max_total_positions = 10
    store.system.min_free_margin = 0.0
    store.system.max_margin_usage_pct = 0.0

    risk = RiskManager(store, _FakeClient())
    existing = [{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}

    # New attempt is itself the scalp secondary - without sec_tickets telling
    # can_open that ticket 100 is ALSO a scalp position (it shares magic 1
    # with the swing primary), the scalp bucket reads 0/1 and this would
    # wrongly be allowed to open a second scalp slot.
    new_cfg = _cfg(symbol="XAUUSD", magic=1, strategy="micro_rev", max_positions=5)
    verdict = risk.can_open(new_cfg, "buy", 0.1, existing, account,
                            sec_tickets=frozenset({100}))
    assert not verdict.ok
    assert "scalp" in verdict.reason


def test_can_open_allows_when_bucket_not_full():
    store = _FakeStore()
    primary = _cfg(symbol="XAUUSD", magic=1, strategy="st_trend",
                   secondary_strategy="micro_rev", max_positions=5)
    store.symbols = {"XAUUSD": primary}
    store.system.max_scalp_positions = 2
    store.system.max_swing_positions = 5
    store.system.max_total_positions = 10
    store.system.min_free_margin = 0.0
    store.system.max_margin_usage_pct = 0.0

    risk = RiskManager(store, _FakeClient())
    existing = [{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}

    new_cfg = _cfg(symbol="XAUUSD", magic=1, strategy="micro_rev", max_positions=5)
    verdict = risk.can_open(new_cfg, "buy", 0.1, existing, account,
                            sec_tickets=frozenset({100}))
    assert verdict.ok


# --------------------------------------------------------------------------- merge_round_trips

def test_merge_round_trips_sums_partial_fills_into_one_trade():
    deals = [
        {"position": 1, "symbol": "EURUSD", "magic": 1, "time": 100,
         "profit": 5.0, "commission": -0.5, "swap": 0.0},
        {"position": 1, "symbol": "EURUSD", "magic": 1, "time": 110,
         "profit": -1.0, "commission": -0.5, "swap": 0.0},
        {"position": 2, "symbol": "EURUSD", "magic": 1, "time": 105,
         "profit": -3.0, "commission": -0.5, "swap": 0.0},
    ]
    merged = MT5Client.merge_round_trips(deals)
    assert len(merged) == 2
    by_pos = {r["position"]: r for r in merged}
    assert by_pos[1]["profit"] == pytest.approx(4.0)
    assert by_pos[1]["commission"] == pytest.approx(-1.0)
    assert by_pos[1]["time"] == 110  # timestamped at the LAST (closing) fill
    # sorted by time ascending: position 2 (t=105) before position 1 (t=110)
    assert [r["position"] for r in merged] == [2, 1]


# --------------------------------------------------------------------------- optimizer.reject_reason

def _result(net_r=10.0, trades=30, pf=1.5, cost_per_trade_r=0.05, score=5.0):
    return {
        "trades": trades, "net_r": net_r, "profit_factor": pf,
        "cost_per_trade_r": cost_per_trade_r, "score": score,
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


# --------------------------------------------------------------------------- apply_secondary guard

class _SecCfg:
    def __init__(self, magic, secondary_strategy, secondary_timeframe):
        self.magic = magic
        self.secondary_strategy = secondary_strategy
        self.secondary_timeframe = secondary_timeframe


class _SecStore:
    def __init__(self, cfg, tagged_tickets, orphan_tickets=None, orphan_scan=None):
        self._cfg = cfg
        self._tagged = tagged_tickets
        self._orphan_tickets = orphan_tickets or []
        self._orphan_scan = orphan_scan or {}
        self.symbols = {"XAUUSD": cfg}
        self.updated_with = None

    def get_setting(self, key, default=None):
        if key == "secondary_tickets":
            return self._tagged
        if key == "secondary_orphan_tickets":
            return self._orphan_tickets
        if key == "secondary_orphan_scan":
            return self._orphan_scan
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch):
        self.updated_with = patch
        for k, v in patch.items():
            setattr(self._cfg, k, v)
        return self._cfg


class _SecClient:
    connected = True

    def __init__(self, positions):
        self._positions = positions

    def positions(self, magic=None, symbol=None):
        return [p for p in self._positions if magic is None or p["magic"] == magic]


def test_apply_secondary_refuses_family_change_with_open_tagged_position():
    cfg = _SecCfg(magic=1, secondary_strategy="micro_rev", secondary_timeframe="M5")
    store = _SecStore(cfg, tagged_tickets=[100])
    client = _SecClient([{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}])
    opt = Optimizer(store=store, client=client)

    new_attempt = {"strategy": "burst", "timeframe": "M10",
                   "best": {"params": {}, "score": 5.0, "holdout": {}, "validation": {},
                            "selection": {}, "positive_ratio": 1.0}}
    result = opt.apply_secondary("XAUUSD", new_attempt)
    assert result["ok"] is False
    assert cfg.secondary_strategy == "micro_rev"  # unchanged


def test_apply_secondary_allows_family_change_with_no_open_tagged_position():
    cfg = _SecCfg(magic=1, secondary_strategy="micro_rev", secondary_timeframe="M5")
    store = _SecStore(cfg, tagged_tickets=[])
    client = _SecClient([])
    opt = Optimizer(store=store, client=client)

    new_attempt = {"strategy": "burst", "timeframe": "M10",
                   "best": {"params": {}, "score": 5.0, "holdout": {}, "validation": {},
                            "selection": {}, "positive_ratio": 1.0}}
    result = opt.apply_secondary("XAUUSD", new_attempt)
    assert result["ok"] is True
    assert store.updated_with["secondary_strategy"] == "burst"


def test_apply_secondary_clear_refused_with_open_tagged_position():
    cfg = _SecCfg(magic=1, secondary_strategy="micro_rev", secondary_timeframe="M5")
    store = _SecStore(cfg, tagged_tickets=[100])
    client = _SecClient([{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}])
    opt = Optimizer(store=store, client=client)

    result = opt.apply_secondary("XAUUSD", None)
    assert result["ok"] is False
    assert cfg.secondary_strategy == "micro_rev"  # unchanged


def test_apply_secondary_refuses_family_change_with_open_orphan_ticket():
    # tagged_tickets empty (never made it into the persisted tag set), but
    # engine.py's H1 orphan tracking still knows about this ticket - identity
    # swap must be held back just like a tagged position would.
    cfg = _SecCfg(magic=1, secondary_strategy="micro_rev", secondary_timeframe="M5")
    store = _SecStore(cfg, tagged_tickets=[], orphan_tickets=[100])
    client = _SecClient([{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}])
    opt = Optimizer(store=store, client=client)

    new_attempt = {"strategy": "burst", "timeframe": "M10",
                   "best": {"params": {}, "score": 5.0, "holdout": {}, "validation": {},
                            "selection": {}, "positive_ratio": 1.0}}
    result = opt.apply_secondary("XAUUSD", new_attempt)
    assert result["ok"] is False
    assert cfg.secondary_strategy == "micro_rev"  # unchanged


def test_apply_secondary_refuses_family_change_with_pending_orphan_scan():
    # A fill just landed and Engine hasn't found its ticket at all yet (0
    # candidates so far) - the symbol-level scan entry alone must block, even
    # before any concrete ticket number exists to check against positions().
    cfg = _SecCfg(magic=1, secondary_strategy="micro_rev", secondary_timeframe="M5")
    store = _SecStore(cfg, tagged_tickets=[],
                      orphan_scan={"XAUUSD": {"magic": 1, "known": [], "since": 0.0}})
    client = _SecClient([])
    opt = Optimizer(store=store, client=client)

    new_attempt = {"strategy": "burst", "timeframe": "M10",
                   "best": {"params": {}, "score": 5.0, "holdout": {}, "validation": {},
                            "selection": {}, "positive_ratio": 1.0}}
    result = opt.apply_secondary("XAUUSD", new_attempt)
    assert result["ok"] is False
    assert cfg.secondary_strategy == "micro_rev"  # unchanged


def test_apply_secondary_allows_family_change_when_orphan_belongs_to_other_symbol():
    # The pending scan is for a different symbol/magic entirely - must not
    # block this one.
    cfg = _SecCfg(magic=1, secondary_strategy="micro_rev", secondary_timeframe="M5")
    store = _SecStore(cfg, tagged_tickets=[],
                      orphan_scan={"EURUSD": {"magic": 2, "known": [], "since": 0.0}})
    client = _SecClient([])
    opt = Optimizer(store=store, client=client)

    new_attempt = {"strategy": "burst", "timeframe": "M10",
                   "best": {"params": {}, "score": 5.0, "holdout": {}, "validation": {},
                            "selection": {}, "positive_ratio": 1.0}}
    result = opt.apply_secondary("XAUUSD", new_attempt)
    assert result["ok"] is True
    assert store.updated_with["secondary_strategy"] == "burst"


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
