"""POST /api/symbols/{symbol} - max_lot/fixed_lot must be capped, not
unbounded (B2): a caller could otherwise size a symbol's lot arbitrarily
large. Ceiling is deliberately 20.0 - a conscious choice, not "smaller is
always safer" - so this pins that exact value rather than "some" ceiling.

Uses minimal fakes for store/client/engine/optimizer, same style as
test_delete_guard.py - no live DB/MT5 dependency needed for this surface.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig
from micofx.web.app import create_app


def _cfg(symbol, magic):
    return SymbolConfig(symbol=symbol, magic=magic)


class _FakeSystem:
    slippage_points = 20

    def to_dict(self):
        return {}


class _FakeStore:
    def __init__(self, symbols):
        self.symbols = symbols
        self.system = _FakeSystem()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch):
        cfg = self.symbols.get(symbol)
        if cfg is None:
            return None
        current = cfg.to_dict()
        for key, value in patch.items():
            if key in current and value is not None:
                current[key] = value
        updated = SymbolConfig.from_dict(current)
        self.symbols[symbol] = updated
        return updated


class _FakeClient:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return None


class _FakeEngine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


def _client():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    app = create_app(store, _FakeClient(), _FakeEngine(), optimizer=None)
    return TestClient(app), store


def test_patch_symbol_rejects_max_lot_over_ceiling():
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"max_lot": 21})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].max_lot != 21


def test_patch_symbol_accepts_max_lot_at_ceiling():
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"max_lot": 20})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].max_lot == 20


def test_patch_symbol_rejects_fixed_lot_over_ceiling():
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"fixed_lot": 20.5})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].fixed_lot != 20.5


def test_patch_symbol_accepts_fixed_lot_at_ceiling():
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"fixed_lot": 20})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].fixed_lot == 20
