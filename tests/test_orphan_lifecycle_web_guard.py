"""H-R1 + M-R1: symbol lifecycle routes (DELETE, seed overwrite, magic
reassignment) and web-side PRIMARY mutations (magic/family/EXIT PATCH) must
treat a pending orphan-scan window (H1's zero-candidate secondary fill, still
invisible to client.positions()) the same way optimizer.apply()/
apply_secondary() and the secondary-side web guards already do. Deleting a
symbol or reassigning its magic while that window is open would free the
magic for reuse (Store.next_magic) while the fill may still turn up under it.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig
from micofx.store import Store
from micofx.web.app import create_app


def _cfg(symbol, magic, **over):
    return SymbolConfig(symbol=symbol, magic=magic, **over)


class _FakeSystem:
    slippage_points = 20

    def to_dict(self):
        return {}


class _FakeStore:
    def __init__(self, symbols, settings=None, defaults=None):
        self.symbols = symbols
        self.system = _FakeSystem()
        self.defaults = defaults or {"symbols": [], "group_presets": {"forex": {}}}
        self._settings = settings or {}
        self.deleted = []
        self.replaced = False
        self.seed_avoid_magics = "unset"

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

    def delete_symbol(self, symbol):
        self.deleted.append(symbol)
        self.symbols.pop(symbol, None)
        return True

    def replace_with_defaults(self):
        self.replaced = True
        n = len(self.symbols)
        self.symbols.clear()
        return n

    def seed_symbols(self, overwrite=False, avoid_magics=None):
        self.seed_avoid_magics = avoid_magics
        return 0

    def next_magic(self, avoid=None):
        used = {c.magic for c in self.symbols.values()}
        scan = self._settings.get("secondary_orphan_scan", {}) or {}
        used |= {int(v.get("magic", -1)) for v in scan.values() if isinstance(v, dict)}
        if avoid:
            used |= set(avoid)
        m = 990101
        while m in used:
            m += 1
        return m

    def add_symbol(self, symbol, group="forex", broker_symbol="", magic=None,
                   enabled=True, avoid_magics=None):
        name = symbol.strip().upper()
        if name in self.symbols:
            raise ValueError(f"{name} zaten portfoyde")
        cfg = SymbolConfig(symbol=name, group=group, broker_symbol=broker_symbol,
                           enabled=enabled,
                           magic=int(magic) if magic is not None else self.next_magic(avoid_magics))
        self.symbols[name] = cfg
        return cfg

    def reset_symbol_to_preset(self, symbol, avoid_magics=None):
        cfg = self.symbols.get(symbol)
        if cfg is None:
            return None
        return cfg


class _FakeClient:
    def __init__(self, positions, connected=True):
        self._positions = positions
        self.connected = connected

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
        self._orphan_scan = {}
        self._orphan_tickets = set()
        self.saved_scan = False
        self.saved_tickets = False

    def _save_orphan_scan(self):
        self.saved_scan = True

    def _save_orphan_tickets(self):
        self.saved_tickets = True


def _client(symbols, positions=None, settings=None, defaults=None, engine=None):
    store = _FakeStore(symbols, settings=settings, defaults=defaults)
    client = _FakeClient(positions or [])
    eng = engine or _FakeEngine()
    app = create_app(store, client, eng, optimizer=None)
    return TestClient(app), store, eng


# --------------------------------------------------------------------- H-R1

def test_delete_symbol_blocked_by_pending_orphan_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store, _eng = _client(symbols, settings=settings)

    res = tc.delete("/api/symbols/XAUUSD")

    assert res.status_code == 409
    assert "XAUUSD" in store.symbols
    assert store.deleted == []


def test_delete_symbol_allowed_when_flat_and_no_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    tc, store, _eng = _client(symbols)

    res = tc.delete("/api/symbols/XAUUSD")

    assert res.status_code == 200
    assert "XAUUSD" not in store.symbols
    assert store.deleted == ["XAUUSD"]


def test_seed_overwrite_blocked_by_pending_orphan_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1), "EURUSD": _cfg("EURUSD", magic=2)}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store, _eng = _client(symbols, settings=settings)

    res = tc.post("/api/symbols-seed", params={"overwrite": "true"})

    assert res.status_code == 409
    assert store.replaced is False
    assert "XAUUSD" in store.symbols


def test_seed_overwrite_allowed_when_no_scan_pending():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    tc, store, _eng = _client(symbols)

    res = tc.post("/api/symbols-seed", params={"overwrite": "true"})

    assert res.status_code == 200
    assert store.replaced is True


def test_create_symbol_avoids_orphan_scan_magic():
    # next_magic() itself is orphan_scan-aware (Store, no client needed) -
    # a brand new symbol must not land on the magic a pending scan still owns.
    symbols = {}
    settings = {"secondary_orphan_scan": {"OLDSYM": {"magic": 990101, "known": [], "since": 0.0}}}
    tc, store, _eng = _client(symbols, settings=settings)

    res = tc.post("/api/symbols", json={"symbol": "EURUSD"})

    assert res.status_code == 200
    assert store.symbols["EURUSD"].magic != 990101


def test_create_symbol_avoids_live_orphan_ticket_magic():
    # This half needs client.positions() (orphan_tickets is just a bare
    # ticket list, no magic stored per-ticket) - _orphan_ticket_magics()
    # resolves it and passes it through as avoid_magics.
    symbols = {}
    settings = {"secondary_orphan_tickets": [777]}
    positions = [{"ticket": 777, "magic": 990101}]
    tc, store, _eng = _client(symbols, positions=positions, settings=settings)

    res = tc.post("/api/symbols", json={"symbol": "EURUSD"})

    assert res.status_code == 200
    assert store.symbols["EURUSD"].magic != 990101


# --------------------------------------------------------------------- M-R1

def test_patch_primary_exit_field_blocked_by_pending_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, sl_atr_mult=1.0)}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store, _eng = _client(symbols, settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={"sl_atr_mult": 2.0})

    assert res.status_code == 409
    assert store.symbols["XAUUSD"].sl_atr_mult == 1.0


def test_patch_primary_family_change_blocked_by_pending_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, strategy="t3_stoch", timeframe="M15")}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store, _eng = _client(symbols, settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={"strategy": "burst", "timeframe": "M5"})

    assert res.status_code == 409
    assert store.symbols["XAUUSD"].strategy == "t3_stoch"


def test_patch_primary_exit_field_allowed_without_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, sl_atr_mult=1.0)}
    tc, store, _eng = _client(symbols)

    res = tc.post("/api/symbols/XAUUSD", json={"sl_atr_mult": 2.0})

    assert res.status_code == 200
    assert store.symbols["XAUUSD"].sl_atr_mult == 2.0


# ------------------------------------------------------------------- NOT-1

def test_bulk_primary_exit_field_blocked_by_pending_scan():
    # bulk_patch only loaded secondary_orphan_scan when a secondary field/
    # param was in the patch - a primary-only EXIT_RISK bulk edit never saw
    # a scan watching the very magic it was about to mutate under.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, sl_atr_mult=1.0)}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store, _eng = _client(symbols, settings=settings)

    res = tc.post("/api/symbols-bulk", json={"symbols": ["XAUUSD"], "patch": {"sl_atr_mult": 2.0}})

    assert res.status_code == 200
    assert res.json()["rejected"] == ["XAUUSD"]
    assert store.symbols["XAUUSD"].sl_atr_mult == 1.0


def test_bulk_primary_family_change_blocked_by_pending_scan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, strategy="t3_stoch", timeframe="M15")}
    settings = {"secondary_orphan_scan": {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}}
    tc, store, _eng = _client(symbols, settings=settings)

    res = tc.post("/api/symbols-bulk",
                  json={"symbols": ["XAUUSD"], "patch": {"strategy": "burst", "timeframe": "M5"}})

    assert res.status_code == 200
    assert res.json()["rejected"] == ["XAUUSD"]
    assert store.symbols["XAUUSD"].strategy == "t3_stoch"


def test_bulk_primary_exit_field_allowed_without_scan_or_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, sl_atr_mult=1.0)}
    tc, store, _eng = _client(symbols)

    res = tc.post("/api/symbols-bulk", json={"symbols": ["XAUUSD"], "patch": {"sl_atr_mult": 2.0}})

    assert res.status_code == 200
    assert res.json().get("rejected", []) == []
    assert store.symbols["XAUUSD"].sl_atr_mult == 2.0


def test_bulk_secondary_regression_still_blocked_by_live_tagged():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, secondary_strategy="t3_stoch",
                              secondary_timeframe="M15")}
    positions = [{"ticket": 500, "magic": 1}]
    settings = {"secondary_tickets": [500]}
    tc, store, _eng = _client(symbols, positions=positions, settings=settings)

    res = tc.post("/api/symbols-bulk",
                  json={"symbols": ["XAUUSD"], "patch": {"secondary_strategy": "burst"}})

    assert res.status_code == 200
    assert res.json()["rejected"] == ["XAUUSD"]
    assert store.symbols["XAUUSD"].secondary_strategy == "t3_stoch"


# ---------------------------------------------------------------------- L1

def test_create_symbol_refused_when_disconnected_with_orphan_tickets():
    settings = {"secondary_orphan_tickets": [777]}
    fake_client = _FakeClient([], connected=False)
    fake_engine = _FakeEngine()
    fake_store = _FakeStore({}, settings=settings)
    app = create_app(fake_store, fake_client, fake_engine, optimizer=None)
    tc = TestClient(app)

    res = tc.post("/api/symbols", json={"symbol": "EURUSD"})

    assert res.status_code == 409
    assert "EURUSD" not in fake_store.symbols


def test_create_symbol_allowed_when_disconnected_without_orphan_tickets():
    fake_client = _FakeClient([], connected=False)
    fake_engine = _FakeEngine()
    fake_store = _FakeStore({})
    app = create_app(fake_store, fake_client, fake_engine, optimizer=None)
    tc = TestClient(app)

    res = tc.post("/api/symbols", json={"symbol": "EURUSD"})

    assert res.status_code == 200
    assert "EURUSD" in fake_store.symbols


def test_reset_recreate_refused_when_disconnected_with_orphan_tickets():
    settings = {"secondary_orphan_tickets": [777]}
    defaults = {"symbols": [{"symbol": "EURUSD", "group": "forex"}],
                "group_presets": {"forex": {}}}
    fake_client = _FakeClient([], connected=False)
    fake_engine = _FakeEngine()
    fake_store = _FakeStore({}, settings=settings, defaults=defaults)
    app = create_app(fake_store, fake_client, fake_engine, optimizer=None)
    tc = TestClient(app)

    res = tc.post("/api/symbols/EURUSD/reset")

    assert res.status_code == 409


def test_reset_existing_symbol_unaffected_by_orphan_tickets():
    # cfg already exists -> reuses cfg.magic, no fresh assignment - L1's
    # disconnected-orphan-ticket guard only applies to the recreate path.
    symbols = {"EURUSD": _cfg("EURUSD", magic=5)}
    settings = {"secondary_orphan_tickets": [777]}
    defaults = {"symbols": [{"symbol": "EURUSD", "group": "forex"}],
                "group_presets": {"forex": {}}}
    tc, store, _eng = _client(symbols, settings=settings, defaults=defaults)

    res = tc.post("/api/symbols/EURUSD/reset")

    assert res.status_code == 200


def test_soft_seed_refused_when_disconnected_with_orphan_tickets():
    settings = {"secondary_orphan_tickets": [777]}
    fake_client = _FakeClient([], connected=False)
    fake_engine = _FakeEngine()
    fake_store = _FakeStore({}, settings=settings)
    app = create_app(fake_store, fake_client, fake_engine, optimizer=None)
    tc = TestClient(app)

    res = tc.post("/api/symbols-seed", params={"overwrite": "false"})

    assert res.status_code == 409


def test_soft_seed_allowed_when_disconnected_without_orphan_tickets():
    fake_client = _FakeClient([], connected=False)
    fake_engine = _FakeEngine()
    fake_store = _FakeStore({})
    app = create_app(fake_store, fake_client, fake_engine, optimizer=None)
    tc = TestClient(app)

    res = tc.post("/api/symbols-seed", params={"overwrite": "false"})

    assert res.status_code == 200


# ----------------------------------------------- NOT-W mid-call disconnect

class _FlipDisconnectClient(_FakeClient):
    """Simulates mt5client.positions(): positions_get fails → [] + connected=False."""

    def positions(self, magic=None, symbol=None):
        self.connected = False
        return []


def test_delete_refuses_when_positions_get_fails_mid_call():
    # Pre-check connected=True, but the guard's positions() call itself flips
    # connected False and returns [] - must NOT read that as flat and delete.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    store = _FakeStore(symbols)
    client = _FlipDisconnectClient([])
    engine = _FakeEngine()
    tc = TestClient(create_app(store, client, engine, optimizer=None))

    res = tc.delete("/api/symbols/XAUUSD")

    assert res.status_code == 503
    assert "XAUUSD" in store.symbols
    assert store.deleted == []
    assert client.connected is False


def test_patch_primary_exit_refuses_when_positions_get_fails_mid_call():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, sl_atr_mult=1.5)}
    store = _FakeStore(symbols)
    client = _FlipDisconnectClient([])
    engine = _FakeEngine()
    tc = TestClient(create_app(store, client, engine, optimizer=None))

    res = tc.post("/api/symbols/XAUUSD", json={"sl_atr_mult": 2.5})

    assert res.status_code == 503
    assert store.symbols["XAUUSD"].sl_atr_mult == 1.5


def test_seed_overwrite_refuses_when_positions_get_fails_mid_call():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    store = _FakeStore(symbols)
    client = _FlipDisconnectClient([])
    engine = _FakeEngine()
    tc = TestClient(create_app(store, client, engine, optimizer=None))

    res = tc.post("/api/symbols-seed", params={"overwrite": "true"})

    assert res.status_code == 503
    assert store.replaced is False


def test_bulk_primary_refuses_when_positions_get_fails_mid_call():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1, sl_atr_mult=1.5)}
    store = _FakeStore(symbols)
    client = _FlipDisconnectClient([])
    engine = _FakeEngine()
    tc = TestClient(create_app(store, client, engine, optimizer=None))

    res = tc.post("/api/symbols-bulk", json={
        "symbols": ["XAUUSD"], "patch": {"sl_atr_mult": 2.5},
    })

    assert res.status_code == 503
    assert store.symbols["XAUUSD"].sl_atr_mult == 1.5


def test_close_ticket_refuses_when_positions_get_fails_mid_call():
    # Mid-call [] must not become 404 "not found" (wrong signal) - 503.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    store = _FakeStore(symbols)
    client = _FlipDisconnectClient([])
    engine = _FakeEngine()
    tc = TestClient(create_app(store, client, engine, optimizer=None))

    res = tc.post("/api/positions/42/close")

    assert res.status_code == 503


def test_create_avoids_orphan_ticket_magics_refuses_mid_call_disconnect():
    # Connected + non-empty orphan_tickets → _orphan_ticket_magics calls
    # positions(); mid-fail must refuse rather than assign with avoid=empty.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    settings = {"secondary_orphan_tickets": [99]}
    store = _FakeStore(symbols, settings=settings)
    client = _FlipDisconnectClient([])
    engine = _FakeEngine()
    tc = TestClient(create_app(store, client, engine, optimizer=None))

    res = tc.post("/api/symbols", json={"symbol": "NEWSYM", "group": "forex"})

    assert res.status_code == 503
    assert "NEWSYM" not in store.symbols


def test_patch_magic_blocked_by_ghost_orphan_scan_magic():
    # Manual magic assignment must not bypass next_magic's scan avoid-set.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    settings = {"secondary_orphan_scan": {"OLDSYM": {"magic": 990101, "known": [], "since": 0.0}}}
    tc, store, _eng = _client(symbols, settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={"magic": 990101})

    assert res.status_code == 409
    assert store.symbols["XAUUSD"].magic == 1


def test_bulk_magic_blocked_by_ghost_orphan_scan_magic():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    settings = {"secondary_orphan_scan": {"OLDSYM": {"magic": 990101, "known": [], "since": 0.0}}}
    tc, store, _eng = _client(symbols, settings=settings)

    res = tc.post("/api/symbols-bulk", json={
        "symbols": ["XAUUSD"], "patch": {"magic": 990101},
    })

    assert res.status_code == 409
    assert store.symbols["XAUUSD"].magic == 1


def test_patch_magic_blocked_by_live_orphan_ticket_magic():
    # Orphan ticket still open under a magic nobody in the portfolio owns -
    # manual PATCH must refuse that magic the same way ghost scan does.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    settings = {"secondary_orphan_tickets": [777]}
    positions = [{"ticket": 777, "magic": 990101, "symbol": "GONE"}]
    tc, store, _eng = _client(symbols, positions=positions, settings=settings)

    res = tc.post("/api/symbols/XAUUSD", json={"magic": 990101})

    assert res.status_code == 409
    assert "orphan" in res.json()["detail"].lower() or "orphan" in res.text.lower() or "990101" in res.text
    assert store.symbols["XAUUSD"].magic == 1


def test_seed_overwrite_clears_live_engine_orphan_maps():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    engine = _FakeEngine()
    engine._orphan_scan = {"XAUUSD": {"magic": 1, "known": [], "since": 0.0}}
    engine._orphan_tickets = {99}
    tc, store, eng = _client(symbols, engine=engine)

    res = tc.post("/api/symbols-seed", params={"overwrite": "true"})

    assert res.status_code == 200
    assert eng._orphan_scan == {}
    assert eng._orphan_tickets == set()
    assert eng.saved_scan is True
    assert eng.saved_tickets is True


def test_soft_seed_always_passes_avoid_magics_when_orphan_tickets_empty():
    # Even with connected=True, avoid must be a set (never the old None ternary).
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=1)}
    tc, store, _eng = _client(symbols)

    res = tc.post("/api/symbols-seed", params={"overwrite": "false"})

    assert res.status_code == 200
    assert store.seed_avoid_magics == set()
