"""Notional dial: equity×N budget via mppu×price, not margin-at-account-lev."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.risk import RiskManager

EQUITY = 247.0
N = 50.0
BROKER = 500
VACANT = 6
# US30-like: $1 per point, price 35000 → $35k notional / lot
PRICE = 35000.0
MPPU_1 = 1.0


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
    target_leverage = N


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()

    def get_setting(self, k, default=None):
        return default


class _Client:
    def info(self, symbol):
        return {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01,
                "point": 1.0, "tick_size": 1.0, "tick_value": 1.0}

    def money_per_price_unit(self, symbol, volume):
        return MPPU_1 * float(volume)

    def tick(self, symbol):
        return {"bid": PRICE, "ask": PRICE, "spread": 0.0}

    def min_stop_distance(self, symbol):
        return 0.0

    def resolve(self, symbol):
        return symbol

    def normalize_volume(self, symbol, lot):
        step = 0.01
        vol = math.floor(float(lot) / step + 1e-9) * step
        return round(max(0.01, min(100.0, vol)), 2)

    def margin_for(self, symbol, lot, side="buy"):
        # Index-like heavy margin (would starve old N/broker margin math).
        return 2000.0 * float(lot)


def _cfg(i: int) -> SymbolConfig:
    c = SymbolConfig(symbol=f"US{i}", magic=300 + i, timeframe="M30",
                     strategy="channel_break")
    c.risk_percent = 1.0
    c.enabled = True
    return c


def test_notional_share_at_lev50_is_equity_times_n_over_vacant():
    store = _Store([_cfg(i) for i in range(VACANT)])
    rm = RiskManager(store, _Client())
    acc = {"equity": EQUITY, "margin_free": EQUITY, "margin": 0.0,
           "leverage": BROKER}
    share = (EQUITY * N) / VACANT
    per_lot = MPPU_1 * PRICE
    expect = share / per_lot  # ~0.0588
    cap = rm._notional_lot_ceiling(_cfg(0), acc, 100.0, positions=[])
    assert cap is not None
    assert abs(cap - expect) < 1e-6


def test_lot_for_lev50_not_zero_on_heavy_margin_index():
    store = _Store([_cfg(i) for i in range(VACANT)])
    rm = RiskManager(store, _Client())
    acc = {"equity": EQUITY, "margin_free": EQUITY, "margin": 0.0,
           "leverage": BROKER}
    # Tight stop → large r_cap so notional / margin bind first.
    lot, note = rm.lot_for(
        _cfg(0), sl_distance=0.5, balance=EQUITY,
        account=acc, positions=[])
    assert lot >= 0.01, f"got {lot} ({note})"
    assert "notional" in note or lot > 0


def test_notional_whole_budget_fallback_funds_min_lot():
    """Equal split may be < min notional; whole book still opens one ticket."""
    store = _Store([_cfg(i) for i in range(VACANT)])

    class _Fat(_Client):
        def info(self, symbol):
            return {"volume_min": 0.1, "volume_max": 100.0, "volume_step": 0.1,
                    "point": 1.0, "tick_size": 1.0, "tick_value": 1.0}

        def normalize_volume(self, symbol, lot):
            step = 0.1
            vol = math.floor(float(lot) / step + 1e-9) * step
            return round(max(0.0, min(100.0, vol)), 1)

        def tick(self, symbol):
            # share $2058 < 0.1*$40k; whole $12350 >= 0.1*$40k
            return {"bid": 40000.0, "ask": 40000.0, "spread": 0.0}

        def money_per_price_unit(self, symbol, volume):
            return 1.0 * float(volume)

        def margin_for(self, symbol, lot, side="buy"):
            return 800.0 * float(lot)  # $80 / 0.1 — whole margin can fund min

    rm = RiskManager(store, _Fat())
    acc = {"equity": EQUITY, "margin_free": EQUITY, "margin": 0.0,
           "leverage": BROKER}
    cap = rm._notional_lot_ceiling(_cfg(0), acc, 100.0, positions=[])
    assert cap is not None and cap + 1e-12 >= 0.1
    lot, note = rm.lot_for(
        _cfg(0), sl_distance=0.5, balance=EQUITY,
        account=acc, positions=[])
    assert lot >= 0.1, f"got {lot} ({note})"
