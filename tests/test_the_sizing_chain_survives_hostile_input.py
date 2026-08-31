"""Adversarial sweep over the paths 31.08 touched on the money side.

These are not "does the number look right" tests - the files next door cover
that. This is the stress pass: feed the sizing chain, the bar-age gate and the
stop floor the values a broker, a corrupt row or a hostile POST can actually
produce, and assert the two properties that must hold no matter what:

  * a lot is either 0 (refused, with a reason) or a finite positive number
    inside [volume_min, volume_max] that never exceeds the 1R ceiling;
  * nothing raises.

A sizing path that throws takes the cycle down; a sizing path that returns
inf, nan or a negative volume sends that to order_send.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from micofx.engine import signal_bar_expired
from micofx.models import SymbolConfig
from micofx.mt5client import MT5Client
from micofx.risk import RiskManager

VOL_MIN, VOL_MAX, STEP = 0.01, 100.0, 0.01
NASTY = [0.0, -1.0, 1e-12, 1e12, float("inf"), float("-inf"), float("nan")]


class _System:
    size_by_edge = True
    lot_multiplier = 1.0
    max_margin_usage_pct = 0.0
    min_free_margin = 0.0
    max_positions = 0
    max_lot = 0.0
    daily_loss_pct = 0.0
    daily_profit_pct = 0.0
    max_concurrent_risk_pct = 0.0
    max_total_positions = 0


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()

    def get_setting(self, k, default=None):
        return default

    def set_setting(self, k, v):
        pass


class _Client:
    def __init__(self, margin=100.0):
        self._margin = margin

    def info(self, symbol):
        return {"volume_min": VOL_MIN, "volume_max": VOL_MAX,
                "volume_step": STEP, "point": 1.0, "tick_size": 1.0,
                "tick_value": 1.0, "filling_mode": 1, "digits": 2}

    def money_per_price_unit(self, symbol, volume):
        return 1.0 * float(volume)

    def min_stop_distance(self, symbol):
        return 0.0

    def resolve(self, symbol):
        return symbol

    def tick(self, symbol):
        return None

    def margin_for(self, symbol, lot, side="buy"):
        return self._margin * float(lot)

    def normalize_volume(self, symbol, lot):
        vol = math.floor(float(lot) / STEP + 1e-9) * STEP
        return round(max(VOL_MIN, min(VOL_MAX, vol)), 2)


def _book(n=3):
    out = []
    for i in range(n):
        c = SymbolConfig(symbol=f"SYM{i}", magic=i + 1, timeframe="M15",
                         strategy="stoch_flip")
        c.risk_percent = 1.0
        c.opt_summary = {"holdout_days": 30.0, "validated": True,
                         "holdout": {"trades": 300, "net_r": 60.0 / (i + 1),
                                     "max_dd_r": 10.0, "expectancy": 0.2}}
        out.append(c)
    return out


def _rm(cfgs=None, margin=100.0):
    cfgs = cfgs or _book()
    return RiskManager(_Store(cfgs), _Client(margin))


def _sane(lot, note):
    assert isinstance(lot, float), note
    assert not math.isnan(lot), note
    assert not math.isinf(lot), note
    assert lot >= 0.0, note
    if lot > 0.0:
        assert VOL_MIN - 1e-12 <= lot <= VOL_MAX + 1e-12, note
    else:
        assert note, "a refusal must carry a reason"


# ------------------------------------------------------------ sizing chain

@pytest.mark.parametrize("sl", NASTY)
def test_a_hostile_stop_distance_never_escapes_the_sizing_chain(sl):
    rm = _rm()
    lot, note = rm.lot_for(rm.store.symbols["SYM0"], sl, 10000.0,
                           account={"equity": 1e4, "margin_free": 1e4,
                                    "margin": 0.0})
    _sane(lot, note)


@pytest.mark.parametrize("bal", NASTY)
def test_a_hostile_balance_never_escapes_the_sizing_chain(bal):
    rm = _rm()
    lot, note = rm.lot_for(rm.store.symbols["SYM0"], 10.0, bal,
                           account={"equity": 1e4, "margin_free": 1e4,
                                    "margin": 0.0})
    _sane(lot, note)


@pytest.mark.parametrize("scale", NASTY)
def test_a_hostile_ai_scale_never_lifts_the_cap(scale):
    """The supervisor throttle may tighten the 1R ceiling, never raise it."""
    rm = _rm()
    cfg = rm.store.symbols["SYM0"]
    account = {"equity": 1e4, "margin_free": 1e4, "margin": 0.0}
    base, _ = rm.lot_for(cfg, 10.0, 10000.0, account=account)
    lot, note = rm.lot_for(cfg, 10.0, 10000.0, ai_scale=scale, account=account)
    _sane(lot, note)
    assert lot <= base + 1e-9, note


@pytest.mark.parametrize("account", [
    None, {}, {"equity": "abc", "margin_free": None, "margin": []},
    {"equity": float("nan"), "margin_free": float("inf"), "margin": -5.0},
    {"equity": -1.0, "margin_free": -1.0, "margin": 1e12},
])
def test_a_corrupt_account_snapshot_never_escapes(account):
    rm = _rm()
    lot, note = rm.lot_for(rm.store.symbols["SYM0"], 10.0, 10000.0,
                           account=account)
    _sane(lot, note)


def test_a_supervisor_hook_that_throws_does_not_take_the_cycle_down():
    rm = _rm()

    def _boom(symbol):
        raise RuntimeError("supervisor exploded")

    rm.supervisor_blocked = _boom
    assert rm._vacant_enabled_count([]) >= 1
    lot, note = rm.lot_for(rm.store.symbols["SYM0"], 10.0, 10000.0,
                           account={"equity": 1e4, "margin_free": 1e4,
                                    "margin": 0.0})
    _sane(lot, note)


def test_the_r_cap_holds_across_the_whole_edge_range():
    """Whatever edge_scale returns, one R must not exceed the cap."""
    rm = _rm()
    cfg = rm.store.symbols["SYM0"]
    account = {"equity": 1e6, "margin_free": 1e6, "margin": 0.0}
    for edge in (0.0, 0.6, 1.0, 2.2, 10.0, 1e6):
        rm.edge_scale = lambda c, e=edge: e
        lot, note = rm.lot_for(cfg, 10.0, 10000.0, account=account)
        _sane(lot, note)
        risk_pct = lot * 10.0 / 10000.0 * 100.0
        assert risk_pct <= RiskManager.AUTO_R_PCT + 1e-9, (edge, note)


# ------------------------------------------------------------ bar-age gate

@pytest.mark.parametrize("tf", NASTY)
def test_a_hostile_timeframe_never_throws_the_age_gate(tf):
    assert signal_bar_expired(1_700_000_000, 1_700_000_600, tf) in (True, False)


@pytest.mark.parametrize("now", NASTY)
def test_a_hostile_clock_never_throws_the_age_gate(now):
    assert signal_bar_expired(1_700_000_000, now, 1800) in (True, False)


def test_a_clock_that_runs_backwards_is_not_an_expiry():
    """A broker stamp behind the bar is a clock fault, not an old signal."""
    assert signal_bar_expired(1_700_000_000, 1_600_000_000, 1800) is False


# ------------------------------------------------------------- stop floor

@pytest.mark.parametrize("stops,freeze", [
    (0, 0), (-5, -5), (10**9, 0), (0, 10**9), (-1, 20),
])
def test_the_stop_floor_never_returns_a_nonsense_distance(monkeypatch, stops, freeze):
    c = object.__new__(MT5Client)
    monkeypatch.setattr(MT5Client, "info", lambda self, s: {
        "point": 0.01, "stops_level": stops, "freeze_level": freeze})
    monkeypatch.setattr(MT5Client, "tick", lambda self, s: None)
    out = MT5Client.min_stop_distance(c, "GER40")
    assert out >= 0.0
    assert not math.isnan(out) and not math.isinf(out)
