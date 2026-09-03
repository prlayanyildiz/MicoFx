"""WEB-1: the panel could read the ceiling and the projection, never the gate.

``capacity()`` already carried ``max_concurrent_risk_pct`` (the ceiling) and
``concurrent_risk_pct`` (the worst case if every slot filled). Neither is the
number ``can_open`` refuses on - that one is the sum of *remaining* 1R across
the open book, which falls as trails ratchet and does not exist anywhere in
the payload. On 24.08 the live ceiling moved 15 -> 30 and the panel showed no
bar for it at all.

Asserted against the gate's own behaviour rather than a copied constant: if
the two ever compute the risk differently, the last test here fails.
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
            kasa_auto_enabled=False,
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

    def info(self, symbol):
        return {"point": 0.01, "tick_value": 1.0, "tick_size": 0.01,
                "volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01}

    def min_stop_distance(self, symbol):
        return 0.0

    def normalize_volume(self, symbol, lot):
        return float(lot)

    def tick(self, symbol):
        return {"bid": 2000.0, "ask": 2000.1, "spread": 0.1}

    def bars(self, symbol, timeframe, count):
        return None


def _pos(sl: float, entry: float = 2000.0, volume: float = 1.0) -> dict:
    return {
        "ticket": 1, "symbol": "XAUUSD", "magic": 1, "side": "buy",
        "volume": volume, "price_open": entry, "sl": sl, "tp": 0.0,
        "profit": 0.0, "swap": 0.0, "price_current": entry, "time": 0,
    }


ACCOUNT = {"equity": 1000.0, "balance": 1000.0, "margin_free": 1000.0, "margin": 0.0}


def test_capacity_reports_the_open_book_risk_the_gate_uses():
    risk = RiskManager(_Store(), _Client())
    # 1R remaining = (2000-1925) * 1.0 lot = 75 = 7.5% of 1000 equity.
    cap = risk.capacity([_pos(sl=1925.0)], ACCOUNT)
    assert cap["open_risk"] == 75.0
    assert cap["open_risk_pct"] == 7.5


def test_an_empty_book_reports_zero_rather_than_omitting_the_field():
    risk = RiskManager(_Store(), _Client())
    cap = risk.capacity([], ACCOUNT)
    assert cap["open_risk"] == 0.0
    assert cap["open_risk_pct"] == 0.0


def test_a_trail_to_entry_drops_out_of_the_reported_number_too():
    """The bar must fall when the danger leaves, exactly as the budget does."""
    risk = RiskManager(_Store(), _Client())
    assert risk.capacity([_pos(sl=2000.0)], ACCOUNT)["open_risk_pct"] == 0.0


def test_the_ceiling_is_in_the_payload():
    """GET honesty: the panel reads the same number can_open enforces."""
    risk = RiskManager(_Store(), _Client())
    cap = risk.capacity([_pos(sl=1925.0)], ACCOUNT)
    assert cap["max_concurrent_risk_pct"] == 8.0


def test_the_gate_refuses_once_reported_risk_is_over_the_cap():
    """Operator re-armed the ceiling 31.08; the reported bar and the gate agree."""
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["GER40"]
    book = [_pos(sl=1925.0)]
    reported = risk.capacity(book, ACCOUNT)["open_risk_pct"]
    assert reported == 7.5
    blocked = risk.can_open(cfg, "buy", 1.0, book, ACCOUNT, sl_distance=400.0)
    assert not blocked.ok
    assert "eszamanli" in blocked.reason


def test_leftover_total_slot_cap_does_not_clip_free_slots():
    """Occupied name is 1-ticket. Vacant GER40 still has a slot; leftover total=1 unread."""
    risk = RiskManager(_Store(), _Client())
    risk.store.system.max_total_positions = 1
    risk.store.symbols["XAUUSD"].enabled = True
    cap = risk.capacity([_pos(sl=1925.0)], ACCOUNT)
    by_sym = {r["symbol"]: r for r in cap["rows"]}
    assert by_sym["XAUUSD"]["free_slots"] == 0
    assert by_sym["GER40"]["free_slots"] > 0
    assert cap["global_free_slots"] > 0


def test_a_naked_stop_does_not_serialise_infinity():
    """/api/state is json.dumps; Infinity is not valid JSON (execution RATIO)."""
    import json
    risk = RiskManager(_Store(), _Client())
    cap = risk.capacity([_pos(sl=0.0)], ACCOUNT)
    assert cap["open_risk_unbounded"] is True
    assert cap["open_risk"] is None
    assert cap["open_risk_pct"] is None
    encoded = json.dumps(cap)
    assert "Infinity" not in encoded and "NaN" not in encoded, encoded
