"""Multi-position scale-in tests: ATR spacing, risk splitting, same-bar guard, and HTTP validation."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import pytest

from micofx.engine import _risk_block_key
from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager
from micofx.web.app import create_app


class _FakeClient:
    connected = True

    def __init__(self, ask: float = 2000.0, bid: float = 2000.0, tick_value: float = 1.0):
        self._ask = ask
        self._bid = bid
        self._tick_value = tick_value

    def set_overrides(self, mapping: dict[str, str]) -> None:
        pass

    def resolve(self, symbol: str) -> str:
        return symbol

    def tick(self, symbol: str) -> dict[str, float] | None:
        return {"ask": self._ask, "bid": self._bid, "spread": 0.1}

    def money_per_price_unit(self, symbol: str, lot: float) -> float:
        return float(lot) * self._tick_value

    def margin_for(self, symbol: str, lot: float, side: str) -> float:
        return float(lot) * 100.0

    def min_stop_distance(self, symbol: str) -> float:
        return 0.1

    def normalize_volume(self, symbol: str, lot: float) -> float:
        return round(lot, 2)

    def info(self, symbol: str) -> dict[str, Any]:
        return {
            "name": symbol,
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01,
            "digits": 2,
            "description": symbol,
        }


class _FakeStore:
    def __init__(self, symbols: dict[str, SymbolConfig] | None = None):
        self.symbols = symbols or {}
        self.system = SystemConfig(
            lot_multiplier=1.0,
            max_concurrent_risk_pct=10.0,
            max_margin_usage_pct=80.0,
            min_free_margin=10.0,
            kasa_auto_enabled=False,
            size_by_edge=False,
        )

        self.settings: dict[str, Any] = {}

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value

    def update_system(self, patch: dict[str, Any], source: str = "") -> SystemConfig:
        d = self.system.to_dict()
        d.update({k: v for k, v in patch.items() if v is not None})
        self.system = SystemConfig.from_dict(d)
        return self.system

    def update_symbol(self, symbol: str, patch: dict[str, Any], source: str = "") -> SymbolConfig:
        cfg = self.symbols[symbol]
        for k, v in patch.items():
            setattr(cfg, k, v)
        return cfg


def test_can_open_allows_multi_position_up_to_cap():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=3, sl_atr_mult=1.0)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient(ask=2020.0, bid=2020.0)
    risk = RiskManager(store, client)

    # 1 open buy position @ 2000.0 with ATR=10.0
    existing = [{"ticket": 101, "symbol": "XAUUSD", "magic": 1, "side": "buy", "price_open": 2000.0, "sl": 1990.0, "volume": 0.01}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 10.0}

    # New entry @ 2020.0 (distance = 20.0 >= 1.0 * ATR 10.0)
    verdict = risk.can_open(cfg, "buy", 0.01, existing, account, sl_distance=10.0, entry_price=2020.0, atr=10.0)
    assert verdict.ok, verdict.reason


def test_can_open_refuses_when_cap_reached():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=3, sl_atr_mult=1.0)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient()
    risk = RiskManager(store, client)

    existing = [
        {"ticket": 101, "symbol": "XAUUSD", "magic": 1, "side": "buy", "price_open": 2000.0, "sl": 1990.0, "volume": 0.01},
        {"ticket": 102, "symbol": "XAUUSD", "magic": 1, "side": "buy", "price_open": 2015.0, "sl": 2005.0, "volume": 0.01},
        {"ticket": 103, "symbol": "XAUUSD", "magic": 1, "side": "buy", "price_open": 2030.0, "sl": 2020.0, "volume": 0.01},
    ]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 30.0}

    verdict = risk.can_open(cfg, "buy", 0.01, existing, account, sl_distance=10.0, entry_price=2045.0, atr=10.0)
    assert not verdict.ok
    assert "sembol pozisyon limiti (3)" in verdict.reason


def test_can_open_refuses_opposite_direction_hedge():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=5, sl_atr_mult=1.0)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient()
    risk = RiskManager(store, client)

    existing = [{"ticket": 101, "symbol": "XAUUSD", "magic": 1, "side": "buy", "price_open": 2000.0, "sl": 1990.0, "volume": 0.01}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 10.0}

    verdict = risk.can_open(cfg, "sell", 0.01, existing, account, sl_distance=10.0, entry_price=2020.0, atr=10.0)
    assert not verdict.ok
    assert "ters yonde acik pozisyon var" in verdict.reason


def test_can_open_refuses_when_atr_spacing_is_too_tight():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=5, sl_atr_mult=1.0)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient()
    risk = RiskManager(store, client)

    # 1 open buy @ 2000.0, ATR=10.0
    existing = [{"ticket": 101, "symbol": "XAUUSD", "magic": 1, "side": "buy", "price_open": 2000.0, "sl": 1990.0, "volume": 0.01}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 10.0}

    # New entry @ 2005.0 -> distance 5.0 < 0.75 * ATR 10.0
    verdict = risk.can_open(cfg, "buy", 0.01, existing, account, sl_distance=10.0, entry_price=2005.0, atr=10.0)
    assert not verdict.ok
    assert "kademe araligi yetersiz" in verdict.reason
    assert _risk_block_key(verdict.reason) == "risk_kademe_aralik"


def test_can_open_allows_scale_in_at_075_atr_spacing():
    """08.09: 0.75 ATR is enough in profit direction (was 1.0 — blocked 0.7–0.85 trends)."""
    from micofx.risk import SCALE_IN_MIN_ATR
    assert SCALE_IN_MIN_ATR == pytest.approx(0.75)

    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=5, sl_atr_mult=1.0)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient()
    risk = RiskManager(store, client)
    existing = [{"ticket": 101, "symbol": "XAUUSD", "magic": 1, "side": "buy",
                 "price_open": 2000.0, "sl": 1990.0, "volume": 0.01}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 10.0}

    # 7.5 price units = 0.75 ATR — must allow
    ok = risk.can_open(cfg, "buy", 0.01, existing, account,
                       sl_distance=10.0, entry_price=2007.5, atr=10.0)
    assert ok.ok, ok.reason

    # Just under — still refuse
    tight = risk.can_open(cfg, "buy", 0.01, existing, account,
                          sl_distance=10.0, entry_price=2007.4, atr=10.0)
    assert not tight.ok
    assert "kademe araligi yetersiz" in tight.reason


def test_can_open_refuses_unmeasurable_spacing():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=5, sl_atr_mult=1.0)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient()
    risk = RiskManager(store, client)

    # Missing price_open on existing position
    existing = [{"ticket": 101, "symbol": "XAUUSD", "magic": 1, "side": "buy", "price_open": 0.0, "sl": 1990.0, "volume": 0.01}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 10.0}

    verdict = risk.can_open(cfg, "buy", 0.01, existing, account, sl_distance=10.0, entry_price=2020.0, atr=10.0)
    assert not verdict.ok
    assert "kademe araligi hesaplanamadi" in verdict.reason
    assert _risk_block_key(verdict.reason) == "risk_kademe_aralik"


def test_can_open_refuses_scale_in_loss_direction_buy():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=5, sl_atr_mult=1.0)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient()
    risk = RiskManager(store, client)

    # 1 open buy @ 2000.0, ATR=10.0
    existing = [{"ticket": 101, "symbol": "XAUUSD", "magic": 1, "side": "buy", "price_open": 2000.0, "sl": 1990.0, "volume": 0.01}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 10.0}

    # New buy entry @ 1980.0: price moved down by 20.0 (distance >= 1.0 ATR, but LOSS direction!)
    verdict = risk.can_open(cfg, "buy", 0.01, existing, account, sl_distance=10.0, entry_price=1980.0, atr=10.0)
    assert not verdict.ok
    assert "kademe araligi kar yonunde yetersiz" in verdict.reason
    assert _risk_block_key(verdict.reason) == "risk_kademe_aralik"


def test_can_open_refuses_scale_in_loss_direction_sell():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=5, sl_atr_mult=1.0)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient()
    risk = RiskManager(store, client)

    # 1 open sell @ 2000.0, ATR=10.0
    existing = [{"ticket": 101, "symbol": "XAUUSD", "magic": 1, "side": "sell", "price_open": 2000.0, "sl": 2010.0, "volume": 0.01}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 10.0}

    # New sell entry @ 2020.0: price moved up by 20.0 (distance >= 1.0 ATR, but LOSS direction!)
    verdict = risk.can_open(cfg, "sell", 0.01, existing, account, sl_distance=10.0, entry_price=2020.0, atr=10.0)
    assert not verdict.ok
    assert "kademe araligi kar yonunde yetersiz" in verdict.reason
    assert _risk_block_key(verdict.reason) == "risk_kademe_aralik"


def test_lot_for_preserves_full_risk_per_ticket():
    cfg_single = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=1, risk_percent=2.0, sl_atr_mult=1.0)
    cfg_multi = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=5, risk_percent=2.0, sl_atr_mult=1.0)

    store = _FakeStore({"XAUUSD": cfg_single})
    client = _FakeClient(tick_value=1.0)
    risk = RiskManager(store, client)

    account = {"equity": 10_000.0, "balance": 10_000.0, "margin_free": 10_000.0, "margin": 0.0}

    lot_single, note_single = risk.lot_for(cfg_single, sl_distance=10.0, balance=10_000.0, account=account)
    lot_multi, note_multi = risk.lot_for(cfg_multi, sl_distance=10.0, balance=10_000.0, account=account)

    # Both tickets maintain full sizing so baseline income is not eaten
    assert lot_single > 0
    assert lot_multi == lot_single
    assert "kademe 5" in note_multi


def test_http_api_accepts_symbol_max_positions_1_to_5():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=1)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient()
    app = create_app(store, client, engine=None, optimizer=None)
    tc = TestClient(app)

    # Valid values 1..5
    for val in (1, 3, 5):
        res = tc.post("/api/symbols/XAUUSD", json={"max_positions": val})
        assert res.status_code == 200, res.text
        assert store.symbols["XAUUSD"].max_positions == val

    # Invalid values
    for bad in (0, -1, 6, 10):
        res = tc.post("/api/symbols/XAUUSD", json={"max_positions": bad})
        assert res.status_code == 400, f"Expected 400 for {bad}"

    # System max_positions remains 400
    res = tc.post("/api/system", json={"max_positions": 5})
    assert res.status_code == 400


def test_kasa_auto_enabled_clears_pins():
    store = _FakeStore({"XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1)})
    client = _FakeClient()
    app = create_app(store, client, engine=None, optimizer=None)
    tc = TestClient(app)

    store.set_setting("kasa_pin_lot_until", 9999999999.0)
    store.set_setting("kasa_pin_conc_until", 9999999999.0)
    assert store.get_setting("kasa_pin_lot_until") > 0

    res = tc.post("/api/system", json={"kasa_auto_enabled": True})
    assert res.status_code == 200
    assert store.get_setting("kasa_pin_lot_until") == 0
    assert store.get_setting("kasa_pin_conc_until") == 0


def test_capacity_slot_left_respects_pos_cap():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=3)
    store = _FakeStore({"XAUUSD": cfg})
    client = _FakeClient()
    rm = RiskManager(store, client)

    # 1 position open on a 3-position cap -> slot_left should be 2
    positions = [{"magic": 1, "symbol": "XAUUSD", "profit": 0.0, "swap": 0.0}]
    account = {"equity": 1000.0, "balance": 1000.0, "margin_free": 1000.0, "margin": 50.0}
    cap = rm.capacity(positions, account, atr_by_symbol={"XAUUSD": 10.0})
    row = cap["rows"][0]
    assert row["open_positions"] == 1
    assert row["free_slots"] == 2

