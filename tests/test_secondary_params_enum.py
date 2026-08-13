"""secondary_params.trail_mode must go through the same enum allowlist as
every other enum field (M4) - top-level _validate_enum_fields never looked
inside this nested dict, so a garbage trail_mode landed straight in
cfg.secondary_params unchecked, on both PATCH /api/symbols/{symbol} and the
bulk PATCH route.
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

    def update_symbol(self, symbol, patch, source=""):
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


def test_patch_symbol_rejects_bad_trail_mode_in_secondary_params():
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={
        "secondary_params": {"trail_mode": "<script>alert(1)</script>", "sl_atr_mult": 1.5},
    })
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].secondary_params == {}


def test_patch_symbol_accepts_valid_trail_mode_in_secondary_params():
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={
        "secondary_params": {"trail_mode": "structure", "sl_atr_mult": 1.5},
    })
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].secondary_params.get("trail_mode") == "structure"


def test_bulk_patch_rejects_bad_trail_mode_in_secondary_params():
    tc, store = _client()
    res = tc.post("/api/symbols-bulk", json={
        "patch": {"secondary_params": {"trail_mode": "garbage"}},
    })
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].secondary_params == {}
