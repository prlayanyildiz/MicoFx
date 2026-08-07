"""API-level test for the DELETE /api/symbols/{symbol} open-position guard.

Uses minimal fakes for store/client/engine/optimizer rather than the real
Store/MT5Client/Engine - those need a live DB file and a running MT5 terminal,
which this test has no business depending on. Only the surface the DELETE
route actually touches is faked.
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
    def to_dict(self):
        return {}


class _FakeStore:
    def __init__(self, symbols, settings=None):
        self.symbols = symbols
        self.system = _FakeSystem()
        self._settings = settings or {}
        self.defaults = {"symbols": [], "group_presets": {}}
        self.replaced = False

    def delete_symbol(self, symbol):
        self.symbols.pop(symbol, None)
        return True

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

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

    def reset_symbol_to_preset(self, symbol):
        cfg = self.symbols.get(symbol)
        if cfg is None:
            return None
        updated = SymbolConfig.from_dict({**cfg.to_dict(), "strategy": "t3_stoch", "timeframe": "M5"})
        self.symbols[symbol] = updated
        return updated

    def replace_with_defaults(self):
        self.replaced = True
        self.symbols.clear()
        return 0

    def seed_symbols(self, overwrite=False):
        return 0


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


class _FakeSupervisor:
    def clear(self, symbol):
        pass


class _FakeExecution:
    def drop_symbol(self, symbol):
        pass


class _FakeEngine:
    def __init__(self):
        self.states = {}
        self.supervisor = _FakeSupervisor()
        self.execution = _FakeExecution()
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


def _client(symbols, positions, settings=None):
    store = _FakeStore(symbols, settings=settings)
    client = _FakeClient(positions)
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None)
    return TestClient(app), store


def test_delete_refuses_symbol_with_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.delete("/api/symbols/XAUUSD")
    assert res.status_code == 409
    assert "XAUUSD" in symbols  # not removed


def test_delete_allows_symbol_with_no_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "COPPER", "magic": 990107, "side": "buy"}]
    tc, store = _client(symbols, positions)

    res = tc.delete("/api/symbols/XAUUSD")
    assert res.status_code == 200
    assert "XAUUSD" not in symbols


def test_delete_unknown_symbol_is_404():
    tc, store = _client({}, [])
    res = tc.delete("/api/symbols/NOPE")
    assert res.status_code == 404


def test_delete_refuses_when_disconnected_even_with_no_visible_positions():
    # Disconnected client.positions() also returns [] - must not be read as
    # "nothing open" and let a destructive mutation through unguarded.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    client = _FakeClient([])
    client.connected = False
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None)
    tc = TestClient(app)

    res = tc.delete("/api/symbols/XAUUSD")
    assert res.status_code == 503
    assert "XAUUSD" in symbols  # not removed


def test_delete_ignores_positions_from_a_different_magic():
    # Same symbol name, different magic - e.g. a leftover manual trade on the
    # same instrument must not block cleaning up the bot's own config for it.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 123456, "side": "buy"}]
    tc, store = _client(symbols, positions)

    res = tc.delete("/api/symbols/XAUUSD")
    assert res.status_code == 200


def test_patch_refuses_magic_change_with_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/symbols/XAUUSD", json={"magic": 990099})
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].magic == 990021  # unchanged


def test_patch_allows_magic_change_with_no_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"magic": 990099})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].magic == 990099


def test_patch_refuses_magic_change_that_collides_with_another_symbol():
    symbols = {
        "XAUUSD": _cfg("XAUUSD", magic=990021),
        "COPPER": _cfg("COPPER", magic=990107),
    }
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"magic": 990107})
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].magic == 990021  # unchanged


def test_bulk_patch_refuses_magic_change_for_multiple_symbols():
    symbols = {
        "XAUUSD": _cfg("XAUUSD", magic=990021),
        "COPPER": _cfg("COPPER", magic=990107),
    }
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols-bulk", json={
        "symbols": ["XAUUSD", "COPPER"], "patch": {"magic": 990500},
    })
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].magic == 990021
    assert store.symbols["COPPER"].magic == 990107


def test_bulk_patch_refuses_magic_change_colliding_with_symbol_outside_targets():
    symbols = {
        "XAUUSD": _cfg("XAUUSD", magic=990021),
        "COPPER": _cfg("COPPER", magic=990107),
    }
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols-bulk", json={
        "symbols": ["XAUUSD"], "patch": {"magic": 990107},
    })
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].magic == 990021


def test_patch_allows_non_magic_fields_with_open_position():
    # The guard is specific to magic changing - an open position must not
    # block every other edit (e.g. flipping enabled off).
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/symbols/XAUUSD", json={"enabled": False})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].enabled is False


def test_patch_refuses_strategy_change_with_open_position():
    # default SymbolConfig is strategy="t3_stoch", timeframe="M5"
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/symbols/XAUUSD", json={"strategy": "st_trend", "timeframe": "M30"})
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].strategy == "t3_stoch"  # unchanged


def test_patch_allows_strategy_change_with_no_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"strategy": "st_trend", "timeframe": "M30"})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].strategy == "st_trend"


def test_bulk_patch_skips_symbol_with_open_position_but_changes_the_rest():
    symbols = {
        "XAUUSD": _cfg("XAUUSD", magic=990021),
        "COPPER": _cfg("COPPER", magic=990107),
    }
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/symbols-bulk", json={
        "symbols": ["XAUUSD", "COPPER"],
        "patch": {"strategy": "st_trend", "timeframe": "M30"},
    })
    assert res.status_code == 200
    body = res.json()
    assert body["rejected"] == ["XAUUSD"]
    assert body["changed"] == 1
    assert store.symbols["XAUUSD"].strategy == "t3_stoch"  # untouched, open position
    assert store.symbols["COPPER"].strategy == "st_trend"  # changed, no open position


def test_bulk_patch_allows_non_strategy_fields_with_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/symbols-bulk", json={
        "symbols": ["XAUUSD"], "patch": {"enabled": False},
    })
    assert res.status_code == 200
    body = res.json()
    assert body["changed"] == 1
    assert "rejected" not in body
    assert store.symbols["XAUUSD"].enabled is False


def test_reset_refuses_with_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/symbols/XAUUSD/reset")
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].strategy == "t3_stoch"


def test_seed_overwrite_refuses_with_open_bot_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/symbols-seed?overwrite=true")
    assert res.status_code == 409
    assert store.replaced is False
    assert "XAUUSD" in store.symbols


def test_patch_refuses_secondary_change_with_open_tagged_position():
    symbols = {"XAUUSD": SymbolConfig(
        symbol="XAUUSD", magic=990021,
        secondary_strategy="micro_rev", secondary_timeframe="M5")}
    positions = [{"ticket": 100, "symbol": "XAUUSD", "magic": 990021, "side": "buy"}]
    tc, store = _client(symbols, positions, settings={"secondary_tickets": [100]})

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_strategy": "burst"})
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].secondary_strategy == "micro_rev"
