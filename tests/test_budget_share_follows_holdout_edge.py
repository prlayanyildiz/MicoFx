"""Margin budget share tracks holdout expectancy, not equal 1/n."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager


class _LinearMarginClient:
    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 100.0, "volume_step": 0.1}

    def money_per_price_unit(self, symbol, lot):
        return 10.0

    def min_stop_distance(self, symbol):
        return 0.0

    def normalize_volume(self, symbol, lot):
        return round(float(lot), 2)

    def resolve(self, symbol):
        return symbol

    def margin_for(self, symbol, lot, side):
        return 100.0 * float(lot)

    def tick(self, symbol):
        return None


def _cfg(symbol: str, magic: int, expectancy: float) -> SymbolConfig:
    return SymbolConfig(
        symbol=symbol,
        magic=magic,
        enabled=True,
        risk_percent=1.0,
        opt_summary={"holdout": {"expectancy": expectancy, "trades": 40, "net_r": expectancy * 40}},
    )


def _rm(cfgs: list[SymbolConfig]) -> RiskManager:
    store = type("S", (), {})()
    store.symbols = {c.symbol: c for c in cfgs}
    store.system = SystemConfig(
        size_by_edge=False,
        lot_multiplier=1.0,
        kasa_auto_enabled=False,
        min_free_margin=0.0,
        max_margin_usage_pct=90.0,
        max_concurrent_risk_pct=0.0,
    )
    store.get_setting = lambda key, default=None: default
    store.set_setting = lambda key, value: None
    rm = RiskManager.__new__(RiskManager)
    rm.store = store
    rm.client = _LinearMarginClient()
    rm.supervisor_blocked = None
    rm.supervisor_edge_health = None
    return rm


def test_stronger_holdout_gets_larger_budget_share():
    strong = _cfg("XAUUSD", 1, 0.25)
    weak = _cfg("BTCUSD", 2, 0.05)
    mid = _cfg("NAS100", 3, 0.10)
    rm = _rm([strong, weak, mid])
    w_strong = rm._symbol_budget_weight(strong, [strong, weak, mid])
    w_weak = rm._symbol_budget_weight(weak, [strong, weak, mid])
    assert w_strong > w_weak
    s_strong = rm._budget_share_frac(strong, [])
    s_weak = rm._budget_share_frac(weak, [])
    assert s_strong > s_weak
    assert pytest.approx(s_strong + s_weak + rm._budget_share_frac(mid, [])) == 1.0


def test_stronger_holdout_gets_larger_margin_lot():
    """900 margin / equal would be 3.0 each; strong must clear that."""
    strong = _cfg("XAUUSD", 1, 0.25)
    weak = _cfg("BTCUSD", 2, 0.05)
    mid = _cfg("NAS100", 3, 0.10)
    rm = _rm([strong, weak, mid])
    account = {"equity": 1000.0, "margin": 0.0, "margin_free": 1000.0}
    lot_s, _ = rm.lot_for(strong, sl_distance=1.0, balance=10_000.0, account=account)
    lot_w, _ = rm.lot_for(weak, sl_distance=1.0, balance=10_000.0, account=account)
    assert lot_s > 3.0
    assert lot_w < 3.0
    assert lot_s > lot_w


def test_equal_expectancy_keeps_equal_split():
    a = _cfg("XAUUSD", 1, 0.0)
    b = _cfg("GER40", 2, 0.0)
    c = _cfg("NAS100", 3, 0.0)
    rm = _rm([a, b, c])
    account = {"equity": 1000.0, "margin": 0.0, "margin_free": 1000.0}
    lot, note = rm.lot_for(a, sl_distance=1.0, balance=10_000.0, account=account)
    assert lot == pytest.approx(3.0)
    assert "marj" in note
