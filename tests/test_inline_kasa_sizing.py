"""Inline kasa: lot_for / can_open use live dial, not 15m patches."""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.risk import RiskManager


class _System:
    size_by_edge = False
    lot_multiplier = 0.5
    max_margin_usage_pct = 80.0
    min_free_margin = 0.0
    max_concurrent_risk_pct = 5.0
    max_scalp_positions = 0
    max_swing_positions = 0
    max_total_positions = 100
    daily_loss_pct = 0.0
    kasa_auto_enabled = True
    target_leverage = 50.0


class _Store:
    def __init__(self, cfgs, system=None):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = system or _System()
        self._settings = {}

    def get_setting(self, k, default=None):
        return self._settings.get(k, default)

    def set_setting(self, k, v):
        self._settings[k] = v


class _Client:
    def info(self, symbol):
        return {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01,
                "point": 1.0, "tick_size": 1.0, "tick_value": 1.0}

    def money_per_price_unit(self, symbol, volume):
        return 1.0 * float(volume)

    def min_stop_distance(self, symbol):
        return 0.0

    def resolve(self, symbol):
        return symbol

    def normalize_volume(self, symbol, lot):
        step = 0.01
        vol = math.floor(float(lot) / step + 1e-9) * step
        return round(max(0.01, min(100.0, vol)), 2)

    def margin_for(self, symbol, lot, side="buy"):
        return 100.0 * float(lot)


def _cfg(i: int) -> SymbolConfig:
    c = SymbolConfig(symbol=f"SYM{i}", magic=100 + i, timeframe="M15",
                     strategy="burst")
    c.risk_percent = 1.0
    c.enabled = True
    return c


def test_live_lot_mult_follows_leverage_dial():
    store = _Store([_cfg(i) for i in range(6)])
    rm = RiskManager(store, _Client())
    acc = {"equity": 247.0, "margin_free": 247.0, "margin": 0.0, "leverage": 500}
    lo = rm.live_lot_multiplier(acc, [])
    store.system.target_leverage = 500.0
    hi = rm.live_lot_multiplier(acc, [])
    assert hi >= lo
    assert lo >= 0.8  # ~1.15 at lev 50


def test_live_lot_mult_pin_keeps_stored():
    store = _Store([_cfg(i) for i in range(6)])
    store.system.lot_multiplier = 0.4
    store.set_setting("kasa_pin_lot_until", time.time() + 3600)
    rm = RiskManager(store, _Client())
    acc = {"equity": 247.0, "margin_free": 247.0, "margin": 0.0, "leverage": 500}
    assert rm.live_lot_multiplier(acc, []) == 0.4


def test_kasa_off_uses_stored():
    store = _Store([_cfg(i) for i in range(6)])
    store.system.kasa_auto_enabled = False
    store.system.lot_multiplier = 0.55
    rm = RiskManager(store, _Client())
    acc = {"equity": 247.0, "margin_free": 247.0, "margin": 0.0, "leverage": 500}
    assert rm.live_lot_multiplier(acc, []) == 0.55


def test_lot_for_note_mentions_kasa():
    store = _Store([_cfg(i) for i in range(6)])
    rm = RiskManager(store, _Client())
    acc = {"equity": 247.0, "margin_free": 247.0, "margin": 0.0, "leverage": 500}
    lot, note = rm.lot_for(_cfg(0), sl_distance=10.0, balance=247.0,
                           account=acc, positions=[])
    assert lot > 0
    assert "kasa x" in note
