"""PATCH /api/symbols/{symbol} and /api/symbols-bulk must treat an
untracked secondary fill (orphan ticket / orphan-scan window - see engine.py's
H1 orphan tracking) as the same "cannot safely touch secondary identity/exit
right now" risk optimizer.apply_secondary() already guards for (H1, this
round). Previously these routes only ever looked at secondary_tickets, so a
fill Engine._try_entry couldn't resolve slipped straight through.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig
from micofx.web.app import create_app


def _cfg(symbol, magic, **over):
    return SymbolConfig(symbol=symbol, magic=magic, secondary_strategy="micro_rev",
                        secondary_timeframe="M5", ensemble_enabled=True, **over)


class _FakeSystem:
    slippage_points = 20

    def to_dict(self):
        return {}


class _FakeStore:
    def __init__(self, symbols, settings=None):
        self.symbols = symbols
        self.system = _FakeSystem()
        self.defaults = {"symbols": [], "group_presets": {}}
        self._settings = settings or {}

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

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

    def __init__(self, positions):
        self._positions = positions

    def positions(self, magic=None, symbol=None):
        out = self._positions
        if magic is not None:
            out = [p for p in out if p["magic"] == magic]
        return out

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return None


class _FakeEngine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


def _client(symbols, positions, settings=None):
    store = _FakeStore(symbols, settings=settings)
    app = create_app(store, _FakeClient(positions), _FakeEngine(), optimizer=None)
    return TestClient(app), store


def test_patch_symbol_secondary_identity_blocked_by_pending_orphan_scan():
    # secondary_tickets is empty (never got tagged) - only the orphan-scan
    # entry knows this magic has an unresolved fill.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store = _client(symbols, positions=[], settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_strategy": "burst"})

    assert res.status_code == 409
    assert store.symbols["XAUUSD"].secondary_strategy == "micro_rev"  # unchanged


def test_patch_symbol_secondary_identity_blocked_by_live_orphan_ticket():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    settings = {"secondary_orphan_tickets": [501]}
    positions = [{"ticket": 501, "magic": 1, "symbol": "XAUUSD"}]
    tc, store = _client(symbols, positions=positions, settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_strategy": "burst"})

    assert res.status_code == 409
    assert store.symbols["XAUUSD"].secondary_strategy == "micro_rev"


def test_patch_symbol_secondary_identity_allowed_when_clear():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    tc, store = _client(symbols, positions=[])

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_strategy": "burst"})

    assert res.status_code == 200
    assert store.symbols["XAUUSD"].secondary_strategy == "burst"


def test_patch_symbol_secondary_exit_field_blocked_by_pending_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1,
                              secondary_params={"trail_start_atr": 1.0})}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store = _client(symbols, positions=[], settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={
        "secondary_params": {"trail_start_atr": 2.0},
    })

    assert res.status_code == 409
    assert store.symbols["XAUUSD"].secondary_params["trail_start_atr"] == 1.0


def test_bulk_patch_secondary_change_rejects_symbol_with_pending_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1), "EURUSD": _cfg("EURUSD", magic=2)}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store = _client(symbols, positions=[], settings=settings)

    res = tc.post("/api/symbols-bulk", json={"patch": {"secondary_strategy": "burst"}})

    assert res.status_code == 200
    body = res.json()
    assert "XAUUSD" in body.get("rejected", [])
    assert store.symbols["XAUUSD"].secondary_strategy == "micro_rev"
    # EURUSD has no pending risk - goes through.
    assert store.symbols["EURUSD"].secondary_strategy == "burst"


def test_bulk_patch_secondary_change_rejects_symbol_with_live_orphan_ticket():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    settings = {"secondary_orphan_tickets": [601]}
    positions = [{"ticket": 601, "magic": 1, "symbol": "XAUUSD"}]
    tc, store = _client(symbols, positions=positions, settings=settings)

    res = tc.post("/api/symbols-bulk", json={"patch": {"secondary_strategy": "burst"}})

    assert res.status_code == 200
    body = res.json()
    assert "XAUUSD" in body.get("rejected", [])
    assert store.symbols["XAUUSD"].secondary_strategy == "micro_rev"
