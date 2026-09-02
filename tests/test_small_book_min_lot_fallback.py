"""Small book: per-name margin share must not block every entry."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.risk import RiskManager


class _System:
    size_by_edge = False
    lot_multiplier = 1.0
    max_margin_usage_pct = 85.0
    min_free_margin = 0.0
    max_concurrent_risk_pct = 50.0
    max_scalp_positions = 0
    max_swing_positions = 0
    max_total_positions = 100
    daily_loss_pct = 0.0


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()

    def get_setting(self, k, default=None):
        return default


class _IndexClient:
    """Index-like margin: 0.1 lot costs $80 (500:1 style)."""

    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 50.0, "volume_step": 0.1}

    def money_per_price_unit(self, symbol, lot):
        return 5.0 * float(lot)

    def min_stop_distance(self, symbol):
        return 1.0

    def resolve(self, symbol):
        return symbol

    def normalize_volume(self, symbol, lot):
        import math
        step = 0.1
        v = math.floor(float(lot) / step + 1e-9) * step
        return round(max(0.1, v), 2)

    def margin_for(self, symbol, lot, side="buy"):
        return 800.0 * float(lot)

    def tick(self, symbol):
        return None


def _cfg(name: str) -> SymbolConfig:
    c = SymbolConfig(symbol=name, magic=hash(name) % 9000 + 100, enabled=True)
    c.risk_percent = 2.0
    c.sl_atr_mult = 1.5
    return c


def _acct(**kw):
    base = {"equity": 200.0, "margin": 0.0, "margin_free": 200.0, "leverage": 500}
    base.update(kw)
    return base


def test_four_vacant_names_still_get_min_lot_on_small_account():
    cfgs = [_cfg(s) for s in ("GER40", "JPN225", "NAS100", "US30")]
    rm = RiskManager(_Store(cfgs), _IndexClient())
    # sl tight enough that min lot stays within MAX_MIN_LOT_OVERSHOOT of 1R
    lot, note = rm.lot_for(cfgs[0], 20.0, 200.0, account=_acct())
    assert lot >= 0.1, note
    assert lot == 0.1, note  # floor, not full margin share


def test_high_leverage_allows_min_lot_when_margin_fits():
    cfgs = [_cfg("GER40")]
    rm = RiskManager(_Store(cfgs), _IndexClient())
    lot, note = rm.lot_for(cfgs[0], 20.0, 200.0, account=_acct())
    assert lot >= 0.1, note


def test_split_still_caps_when_whole_book_cannot_fund_min_lot():
    cfgs = [_cfg("GER40")]
    rm = RiskManager(_Store(cfgs), _IndexClient())
    lot, note = rm.lot_for(cfgs[0], 50.0, 50.0, account=_acct(equity=50.0, margin_free=50.0))
    assert lot == 0.0
    assert "atlandi" in note


def test_wide_stop_skips_when_min_lot_blows_past_1r_overshoot():
    """C1: 1:500 must not unlock full margin share past the overshoot guard."""
    cfgs = [_cfg("GER40")]
    rm = RiskManager(_Store(cfgs), _IndexClient())
    lot, note = rm.lot_for(cfgs[0], 50.0, 200.0, account=_acct())
    assert lot == 0.0, note
    assert "atlandi" in note
