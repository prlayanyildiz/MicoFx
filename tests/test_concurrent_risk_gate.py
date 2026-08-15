"""AU1: concurrent 1R was a spreadsheet number, not a can_open gate.

AT8 measured the live book at 3.68% concurrent risk only because 1:100
margin happened to bind first. can_open checked slots and margin, never
the sum of open 1R. Raising leverage to 1:500 would drop that accidental
ceiling and leave the 8% budget as a note on a page.

Found on the AT8 measurement (2026-08-16): unclamped raw book is 19.65%
1R with no engine stop. This test is the defect — a 7.5% open book plus
a 1% entry must refuse, and a trail pulled to entry must free the budget.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager


class _Store:
    def __init__(self) -> None:
        self.system = SystemConfig(
            max_total_positions=20,
            max_scalp_positions=0,
            max_swing_positions=0,
            min_free_margin=0.0,
            max_margin_usage_pct=0.0,
        )
        self.system.max_concurrent_risk_pct = 8.0
        self.symbols = {
            "XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1, max_positions=10),
        }

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass


class _Client:
    def resolve(self, symbol):
        return symbol

    def margin_for(self, symbol, lot, side):
        return 1.0

    def money_per_price_unit(self, symbol, lot):
        return float(lot)


def _pos(sl: float, entry: float = 2000.0, volume: float = 1.0, side: str = "buy") -> dict:
    return {
        "ticket": 1, "symbol": "XAUUSD", "magic": 1, "side": side,
        "volume": volume, "price_open": entry, "sl": sl,
    }


def test_a_one_percent_entry_is_refused_when_open_risk_is_already_7_5():
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["XAUUSD"]
    # 1R remaining = (2000-1925)*1.0 lot = 75 = 7.5% of 1000 equity.
    open_now = [_pos(sl=1925.0)]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}
    blocked = risk.can_open(cfg, "buy", 1.0, open_now, account, sl_distance=10.0)
    assert not blocked.ok
    assert "eszamanli risk" in blocked.reason


def test_a_point_four_percent_entry_fits_the_same_7_5_book():
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["XAUUSD"]
    open_now = [_pos(sl=1925.0)]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}
    allowed = risk.can_open(cfg, "buy", 1.0, open_now, account, sl_distance=4.0)
    assert allowed.ok, allowed.reason


def test_a_stop_trailed_to_entry_drops_out_of_the_budget():
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["XAUUSD"]
    # Same ticket, SL now at entry: remaining 1R is 0, so a 1% entry fits.
    open_now = [_pos(sl=2000.0)]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}
    allowed = risk.can_open(cfg, "buy", 1.0, open_now, account, sl_distance=10.0)
    assert allowed.ok, allowed.reason


def test_zero_disables_the_concurrent_risk_gate():
    store = _Store()
    store.system.max_concurrent_risk_pct = 0.0
    risk = RiskManager(store, _Client())
    cfg = store.symbols["XAUUSD"]
    open_now = [_pos(sl=1925.0)]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}
    allowed = risk.can_open(cfg, "buy", 1.0, open_now, account, sl_distance=10.0)
    assert allowed.ok, allowed.reason
