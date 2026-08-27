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
    return SymbolConfig(symbol=symbol, magic=magic, **over)


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


def test_patch_symbol_family_blocked_by_pending_orphan_scan():
    # secondary_tickets is empty (never got tagged) - only the orphan-scan
    # entry knows this magic has an unresolved fill. Identity fields of the
    # retired second leg are ignored; the scan still blocks a primary family swap.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, strategy="stoch_flip")}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store = _client(symbols, positions=[], settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={"strategy": "burst"})

    assert res.status_code == 400
    assert store.symbols["XAUUSD"].strategy == "stoch_flip"


def test_patch_symbol_family_blocked_by_live_orphan_ticket():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, strategy="stoch_flip")}
    settings = {"secondary_orphan_tickets": [501]}
    positions = [{"ticket": 501, "magic": 1, "symbol": "XAUUSD"}]
    tc, store = _client(symbols, positions=positions, settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={"strategy": "burst"})

    assert res.status_code == 400
    assert store.symbols["XAUUSD"].strategy == "stoch_flip"


def test_patch_symbol_family_refused_when_clear():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, strategy="stoch_flip")}
    tc, store = _client(symbols, positions=[])

    res = tc.post("/api/symbols/XAUUSD", json={"strategy": "burst"})

    assert res.status_code == 400
    assert store.symbols["XAUUSD"].strategy == "stoch_flip"


def test_patch_symbol_exit_field_blocked_by_pending_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, sl_atr_mult=1.0)}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store = _client(symbols, positions=[], settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={"sl_atr_mult": 2.0})

    assert res.status_code == 400
    assert store.symbols["XAUUSD"].sl_atr_mult == 1.0


def test_bulk_patch_family_change_rejects_symbol_with_pending_scan():
    symbols = {
        "XAUUSD": _cfg("XAUUSD", magic=1, strategy="stoch_flip"),
        "EURUSD": _cfg("EURUSD", magic=2, strategy="stoch_flip"),
    }
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store = _client(symbols, positions=[], settings=settings)

    res = tc.post("/api/symbols-bulk", json={"patch": {"strategy": "burst"}})

    assert res.status_code == 400
    assert store.symbols["XAUUSD"].strategy == "stoch_flip"
    assert store.symbols["EURUSD"].strategy == "stoch_flip"


def test_bulk_patch_family_change_rejects_symbol_with_live_orphan_ticket():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, strategy="stoch_flip")}
    settings = {"secondary_orphan_tickets": [601]}
    positions = [{"ticket": 601, "magic": 1, "symbol": "XAUUSD"}]
    tc, store = _client(symbols, positions=positions, settings=settings)

    res = tc.post("/api/symbols-bulk", json={"patch": {"strategy": "burst"}})

    assert res.status_code == 400
    assert store.symbols["XAUUSD"].strategy == "stoch_flip"
