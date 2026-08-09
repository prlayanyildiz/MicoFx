"""POST /api/opt/apply must reject NaN-string params and bad enum values
before they ever reach optimizer.apply()/store.update_symbol() - the same
gate PATCH /api/symbols/{symbol} already has, closed here too since
optimizer.apply() writes into the same SymbolConfig unvalidated field-by-field.

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

    def opt_history(self, symbol, limit):
        return []

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


class _FakeEngine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


class _FakeOptimizer:
    """apply() records the call so a test can assert it was never reached."""

    def __init__(self):
        self.calls = []

    def apply(self, symbol, params, score, detail=None, timeframe=None, strategy=None):
        self.calls.append((symbol, params, score, timeframe, strategy))
        return {"ok": True, "applied": True}


def _client():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    client = _FakeClient()
    engine = _FakeEngine()
    optimizer = _FakeOptimizer()
    app = create_app(store, client, engine, optimizer)
    return TestClient(app), optimizer


def test_opt_apply_rejects_nan_string_param():
    tc, optimizer = _client()
    res = tc.post("/api/opt/apply", json={
        "symbol": "XAUUSD",
        "params": {"sl_atr_mult": "NaN", "tp_atr_mult": 2.0},
    })
    assert res.status_code == 400
    assert optimizer.calls == []


def test_opt_apply_rejects_infinity_param():
    tc, optimizer = _client()
    res = tc.post("/api/opt/apply", json={
        "symbol": "XAUUSD",
        "params": {"sl_atr_mult": "Infinity"},
    })
    assert res.status_code == 400
    assert optimizer.calls == []


def test_opt_apply_rejects_invalid_trail_mode():
    tc, optimizer = _client()
    res = tc.post("/api/opt/apply", json={
        "symbol": "XAUUSD",
        "params": {"sl_atr_mult": 1.5, "trail_mode": "<script>alert(1)</script>"},
    })
    assert res.status_code == 400
    assert optimizer.calls == []


def test_opt_apply_rejects_invalid_strategy():
    tc, optimizer = _client()
    res = tc.post("/api/opt/apply", json={
        "symbol": "XAUUSD",
        "params": {"sl_atr_mult": 1.5},
        "strategy": "not_a_real_strategy",
    })
    assert res.status_code == 400
    assert optimizer.calls == []


def test_opt_apply_rejects_nan_string_score():
    tc, optimizer = _client()
    res = tc.post("/api/opt/apply", json={
        "symbol": "XAUUSD",
        "params": {"sl_atr_mult": 1.5},
        "score": "NaN",
    })
    assert res.status_code == 400
    assert optimizer.calls == []


def test_opt_apply_rejects_infinity_score():
    tc, optimizer = _client()
    res = tc.post("/api/opt/apply", json={
        "symbol": "XAUUSD",
        "params": {"sl_atr_mult": 1.5},
        "score": "Infinity",
    })
    assert res.status_code == 400
    assert optimizer.calls == []


def test_opt_apply_run_id_path_score_also_validated():
    tc, optimizer = _client()

    class _StoreWithHistory(_FakeStore):
        def opt_history(self, symbol, limit):
            return [{"id": 9, "symbol": symbol, "params": {"sl_atr_mult": 1.5},
                     "score": float("nan"), "timeframe": "M15", "strategy": "t3_stoch",
                     "validated": True}]

    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _StoreWithHistory(symbols)
    app = create_app(store, _FakeClient(), _FakeEngine(), optimizer)
    tc2 = TestClient(app)

    res = tc2.post("/api/opt/apply", json={"symbol": "XAUUSD", "run_id": 9})
    assert res.status_code == 400
    assert optimizer.calls == []


def test_opt_apply_accepts_valid_params():
    tc, optimizer = _client()
    res = tc.post("/api/opt/apply", json={
        "symbol": "XAUUSD",
        "params": {"sl_atr_mult": 1.5, "tp_atr_mult": 2.0, "trail_mode": "atr"},
        "strategy": "t3_stoch", "timeframe": "M15",
    })
    assert res.status_code == 200
    assert len(optimizer.calls) == 1


def test_opt_apply_run_id_path_also_validated():
    """params pulled from stored opt history go through the same gate."""
    tc, optimizer = _client()

    class _StoreWithHistory(_FakeStore):
        def opt_history(self, symbol, limit):
            return [{"id": 7, "symbol": symbol, "params": {"sl_atr_mult": "NaN"},
                     "score": 1.0, "timeframe": "M15", "strategy": "t3_stoch",
                     "validated": True}]

    # Swap in a store whose history carries a bad param.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _StoreWithHistory(symbols)
    app = create_app(store, _FakeClient(), _FakeEngine(), optimizer)
    tc2 = TestClient(app)

    res = tc2.post("/api/opt/apply", json={"symbol": "XAUUSD", "run_id": 7})
    assert res.status_code == 400
    assert optimizer.calls == []
