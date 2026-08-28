"""Leftover max_concurrent_risk_pct must not refuse an entry.

Operator 27.08: the 30% book-wide 1R ceiling is gone. Lot is risk% of
balance; same-symbol is one ticket. A stored 8 or 30 must not still bind.
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
            "GER40": SymbolConfig(symbol="GER40", magic=2, max_positions=10),
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


def test_leftover_eight_percent_does_not_refuse_a_fat_book():
    """1R remaining = 7.5% plus a 1% entry used to trip 8. Now it must pass."""
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["GER40"]
    open_now = [_pos(sl=1925.0)]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}
    allowed = risk.can_open(cfg, "buy", 1.0, open_now, account, sl_distance=10.0)
    assert allowed.ok, allowed.reason
    assert "eszamanli" not in (allowed.reason or "")


def test_leftover_thirty_percent_is_unread_too():
    store = _Store()
    store.system.max_concurrent_risk_pct = 30.0
    risk = RiskManager(store, _Client())
    cfg = store.symbols["GER40"]
    open_now = [_pos(sl=1925.0)]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}
    allowed = risk.can_open(cfg, "buy", 1.0, open_now, account, sl_distance=400.0)
    assert allowed.ok, allowed.reason


def test_a_missing_stop_still_blocks_the_next_fill():
    """sl=0 is not free room. manage_positions reports STOPSUZ and does not close."""
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["XAUUSD"]
    open_now = [_pos(sl=0.0)]
    account = {"equity": 1000.0, "margin_free": 1000.0, "margin": 0.0}
    blocked = risk.can_open(cfg, "buy", 1.0, open_now, account, sl_distance=4.0)
    assert not blocked.ok
    assert "stopsuz" in blocked.reason
    assert risk.remaining_position_risk(open_now[0]) == float("inf")
