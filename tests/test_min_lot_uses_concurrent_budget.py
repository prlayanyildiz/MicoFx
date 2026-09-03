"""Past 1.5x 1R overshoot, min lot may still open if concurrent budget fits."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager


class _Client:
    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 50.0, "volume_step": 0.1}

    def money_per_price_unit(self, symbol, lot=1.0):
        return 5.0

    def min_stop_distance(self, symbol):
        return 1.0

    def resolve(self, symbol):
        return symbol

    def normalize_volume(self, symbol, lot):
        return round(float(lot), 2)

    def margin_for(self, symbol, lot, side="buy"):
        return 50.0 * float(lot)  # cheap margin so share funds 0.1

    def tick(self, symbol):
        return None


def _rm(*, concurrent: float = 50.0) -> RiskManager:
    cfg = SymbolConfig(symbol="US30", magic=1, enabled=True, risk_percent=2.0)
    store = type("S", (), {})()
    store.symbols = {cfg.symbol: cfg}
    store.system = SystemConfig(
        size_by_edge=False, lot_multiplier=1.0, kasa_auto_enabled=False,
        min_free_margin=0.0, max_margin_usage_pct=90.0,
        max_concurrent_risk_pct=concurrent,
    )
    store.get_setting = lambda *a, **k: None
    rm = RiskManager.__new__(RiskManager)
    rm.store = store
    rm.client = _Client()
    rm.supervisor_blocked = None
    return rm


def test_min_lot_opens_when_past_1_5x_but_concurrent_budget_fits():
    """sl wide → r_cap ~0.04, floor 0.1 (~2.5x). Concurrent 50% has room."""
    rm = _rm(concurrent=50.0)
    acc = {"equity": 200.0, "margin": 0.0, "margin_free": 200.0, "leverage": 500}
    # r_cap = 200*2%*1 / (50*5) = 4/250 = 0.016; floor/r_cap = 6.25 → need
    # a milder stop so overshoot is ~2.5 not absurd.
    # r_cap = 4 / (sl*5) = 0.1/2.5 = 0.04 → sl*5 = 100 → sl = 20
    lot, note = rm.lot_for(rm.store.symbols["US30"], 20.0, 200.0, account=acc)
    assert lot == pytest.approx(0.1), note
    assert "eszamanli" in note.lower() or "min lot" in note.lower()


def test_min_lot_still_skips_when_concurrent_is_off():
    rm = _rm(concurrent=0.0)
    acc = {"equity": 200.0, "margin": 0.0, "margin_free": 200.0, "leverage": 500}
    lot, note = rm.lot_for(rm.store.symbols["US30"], 20.0, 200.0, account=acc)
    assert lot == 0.0
    assert "atlandi" in note


def test_min_lot_opens_near_live_us30_overshoot():
    """Live US30 ~3.22x (0.1 / 0.031) must clear the concurrent door."""
    rm = _rm(concurrent=50.0)
    acc = {"equity": 236.0, "margin": 0.0, "margin_free": 236.0, "leverage": 500}
    # r_cap = 236*2%/100 / (sl*5) = 0.031 → sl = 4.72/(0.031*5) wait:
    # r_cap = 4.72 / (sl*5) = 0.031 → sl*5 = 152.258 → sl ≈ 30.45
    lot, note = rm.lot_for(rm.store.symbols["US30"], 30.45, 236.0, account=acc)
    assert lot == pytest.approx(0.1), note
    assert "eszamanli" in note.lower()


def test_extreme_overshoot_still_skips_even_with_concurrent_room():
    """Hard ceiling (3.5x) — do not unlock 10% book fills."""
    rm = _rm(concurrent=50.0)
    acc = {"equity": 200.0, "margin": 0.0, "margin_free": 200.0, "leverage": 500}
    # r_cap = 4/(50*5) = 0.016; floor/r_cap = 6.25 > 3.5
    lot, note = rm.lot_for(rm.store.symbols["US30"], 50.0, 200.0, account=acc)
    assert lot == 0.0, note
    assert "atlandi" in note
