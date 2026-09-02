"""Auto 1R cap must not vanish behind leverage or margin share (C1).

On ~$225 + 1:500, ``r_cap`` (2% of balance) sits under broker ``volume_min``.
The old ``lev >= 100`` branch then took ``min(auto, ceiling)`` — full margin
share — so each index entry risked ~10% of equity instead of ~2%.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.risk import RiskManager


class _System:
    size_by_edge = False
    lot_multiplier = 0.92
    max_margin_usage_pct = 78.0
    min_free_margin = 0.0
    max_concurrent_risk_pct = 46.0
    max_scalp_positions = 0
    max_swing_positions = 0
    max_total_positions = 100
    daily_loss_pct = 0.0


class _Store:
    def __init__(self):
        self.system = _System()
        self.symbols = {"GER40": SymbolConfig(
            symbol="GER40", magic=1, enabled=True, risk_percent=1.0)}

    def get_setting(self, key, default=None):
        return default


class _Client:
    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 50.0, "volume_step": 0.1}

    def money_per_price_unit(self, symbol, lot=1.0):
        return 1.0 * float(lot)

    def min_stop_distance(self, symbol):
        return 1.0

    def normalize_volume(self, symbol, lot):
        return round(max(0.0, float(lot)), 2)

    def margin_for(self, symbol, lot, side="buy"):
        return 0.5 * float(lot)

    def resolve(self, symbol):
        return symbol

    def tick(self, symbol):
        return None


def _acct(**kw):
    base = {"balance": 225.0, "equity": 225.0, "margin_free": 200.0,
            "leverage": 500, "margin": 0.0}
    base.update(kw)
    return base


def test_high_leverage_min_lot_stays_within_1r_overshoot_not_margin_share():
    rm = RiskManager(_Store(), _Client())
    # r_cap ≈ 225*2%*0.92 / 50 ≈ 0.0828; floor 0.1 → overshoot ~1.21 < 3
    lot, note = rm.lot_for(
        _Store().symbols["GER40"], sl_distance=50.0, balance=225.0,
        account=_acct(), side="buy", positions=[])
    assert lot == 0.1, (lot, note)
    # Must not have taken a multi-lot margin share.
    assert lot <= 0.1 + 1e-9


def test_min_lot_far_above_1r_cap_skips_instead_of_margin_sizing():
    rm = RiskManager(_Store(), _Client())
    # r_cap ≈ 50*2%*0.92 / 200 ≈ 0.0046; floor/r_cap ≫ 3 → skip
    lot, note = rm.lot_for(
        _Store().symbols["GER40"], sl_distance=200.0, balance=50.0,
        account=_acct(balance=50.0, equity=50.0, margin_free=40.0),
        side="buy", positions=[])
    assert lot == 0.0, (lot, note)
    assert "atlandi" in note
