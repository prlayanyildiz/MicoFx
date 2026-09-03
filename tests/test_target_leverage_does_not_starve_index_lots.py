"""target_leverage=50 must not zero index lots via N/broker margin shrink."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.risk import RiskManager


class _System:
    size_by_edge = False
    lot_multiplier = 1.0
    max_margin_usage_pct = 80.0
    min_free_margin = 0.0
    max_concurrent_risk_pct = 50.0
    max_scalp_positions = 0
    max_swing_positions = 0
    max_total_positions = 100
    daily_loss_pct = 0.0
    kasa_auto_enabled = True
    target_leverage = 50.0


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()

    def get_setting(self, k, default=None):
        return default


class _IndexClient:
    """US30-like: 0.1 min lot needs ~$80 margin (not 1:500 forex)."""

    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 50.0, "volume_step": 0.1,
                "point": 1.0, "tick_size": 1.0, "tick_value": 1.0}

    def money_per_price_unit(self, symbol, volume):
        return 1.0 * float(volume)

    def min_stop_distance(self, symbol):
        return 0.0

    def resolve(self, symbol):
        return symbol

    def normalize_volume(self, symbol, lot):
        step = 0.1
        vol = math.floor(float(lot) / step + 1e-9) * step
        return round(max(0.0, min(50.0, vol)), 1)

    def margin_for(self, symbol, lot, side="buy"):
        return 800.0 * float(lot)  # $80 per 0.1


def _cfg(i: int) -> SymbolConfig:
    c = SymbolConfig(symbol=f"IDX{i}", magic=200 + i, timeframe="M30",
                     strategy="channel_break")
    c.risk_percent = 1.0
    c.enabled = True
    return c


def test_lev50_does_not_zero_index_min_lot():
    """Old bug: equity*(50/500)=$25 / 6 < $80 min → lot 0.00."""
    store = _Store([_cfg(i) for i in range(6)])
    rm = RiskManager(store, _IndexClient())
    acc = {"equity": 247.0, "margin_free": 247.0, "margin": 0.0, "leverage": 500}
    # Wide stop so 1R does not bind under min lot overshoot skip wrongly —
    # use tight stop so r_cap is large vs margin share.
    lot, note = rm.lot_for(
        _cfg(0), sl_distance=1.0, balance=247.0,
        account=acc, positions=[])
    assert lot >= 0.1, f"expected min lot, got {lot} ({note})"
