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
    slippage_points = 20

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
        self.closed_tickets = []

    def positions(self, magic=None, symbol=None):
        out = self._positions
        if magic is not None:
            out = [p for p in out if p["magic"] == magic]
        return out

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return None

    def close_position(self, ticket, slippage, comment, volume=None, fill=None):
        self.closed_tickets.append(int(ticket))
        # Full close by default: remove from the live book so re-diff honesty
        # (DONE_PARTIAL path keeps the ticket) matches production.
        gone = [p for p in self._positions if p["ticket"] == int(ticket)]
        self._positions = [p for p in self._positions if p["ticket"] != int(ticket)]
        if fill is not None and gone:
            fill.update({"volume": float(gone[0].get("volume", 0.1)),
                         "symbol": gone[0].get("symbol", ""), "side": "buy",
                         "requested": 0.0, "price": 0.0, "risk_dist": 0.0})
        return True


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


# ------------------------------------------------------------ internal-only fields

def test_patch_refuses_pending_exit_patch_written_directly():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"pending_exit_patch": {"sl_atr_mult": 99.0}})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].pending_exit_patch == {}


def test_patch_refuses_pending_secondary_exit_patch_written_directly():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"pending_secondary_exit_patch": {"magic": 1}})
    assert res.status_code == 400


# --------------------------------------------------------------- exit/risk field guard

def test_patch_refuses_exit_field_change_with_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/symbols/XAUUSD", json={"sl_atr_mult": 2.5})
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].sl_atr_mult != 2.5


def test_patch_allows_exit_field_change_with_no_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"sl_atr_mult": 2.5})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].sl_atr_mult == 2.5


def test_bulk_patch_refuses_exit_field_change_with_open_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 1, "symbol": "XAUUSD", "magic": 990021, "side": "sell"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/symbols-bulk", json={
        "symbols": ["XAUUSD"], "patch": {"trail_start_atr": 3.0},
    })
    assert res.status_code == 200
    body = res.json()
    assert body["rejected"] == ["XAUUSD"]
    assert store.symbols["XAUUSD"].trail_start_atr != 3.0


# ----------------------------------------------------- secondary_params nested guard

def test_patch_refuses_non_dict_secondary_params():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_params": "wipe"})
    assert res.status_code == 400


def test_patch_refuses_nan_inside_secondary_params():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    # httpx's own json= encoder rejects NaN before it can even be sent - send
    # the raw body instead so the (Python json-based) server-side parser,
    # which does accept the NaN literal, is what actually gets exercised.
    res = tc.post("/api/symbols/XAUUSD", content=b'{"secondary_params": {"sl_atr_mult": NaN}}',
                  headers={"Content-Type": "application/json"})
    assert res.status_code == 400


def test_patch_refuses_secondary_params_exit_field_change_with_open_tagged_position():
    symbols = {"XAUUSD": SymbolConfig(
        symbol="XAUUSD", magic=990021,
        secondary_strategy="micro_rev", secondary_timeframe="M5",
        secondary_params={"sl_atr_mult": 1.0, "adx_min": 20.0})}
    positions = [{"ticket": 100, "symbol": "XAUUSD", "magic": 990021, "side": "buy"}]
    tc, store = _client(symbols, positions, settings={"secondary_tickets": [100]})

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_params": {"sl_atr_mult": 2.0, "adx_min": 20.0}})
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].secondary_params["sl_atr_mult"] == 1.0


def test_patch_refuses_secondary_params_wipe_by_omission_with_open_tagged_position():
    # A replacement dict that simply DROPS a previously-set exit key (instead
    # of explicitly changing its value) must be caught too - full-replace
    # semantics mean the omission silently removes it.
    symbols = {"XAUUSD": SymbolConfig(
        symbol="XAUUSD", magic=990021,
        secondary_strategy="micro_rev", secondary_timeframe="M5",
        secondary_params={"sl_atr_mult": 1.0, "adx_min": 20.0})}
    positions = [{"ticket": 100, "symbol": "XAUUSD", "magic": 990021, "side": "buy"}]
    tc, store = _client(symbols, positions, settings={"secondary_tickets": [100]})

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_params": {"adx_min": 20.0}})
    assert res.status_code == 409
    assert store.symbols["XAUUSD"].secondary_params["sl_atr_mult"] == 1.0


def test_patch_allows_secondary_params_entry_field_change_with_open_tagged_position():
    # Entry-signal params (not in EXIT_RISK_FIELDS) are safe to land
    # immediately even with a tagged position open.
    symbols = {"XAUUSD": SymbolConfig(
        symbol="XAUUSD", magic=990021,
        secondary_strategy="micro_rev", secondary_timeframe="M5",
        secondary_params={"sl_atr_mult": 1.0, "adx_min": 20.0})}
    positions = [{"ticket": 100, "symbol": "XAUUSD", "magic": 990021, "side": "buy"}]
    tc, store = _client(symbols, positions, settings={"secondary_tickets": [100]})

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_params": {"sl_atr_mult": 1.0, "adx_min": 25.0}})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].secondary_params["adx_min"] == 25.0


# ------------------------------------------------------------------- enum fields

def test_patch_refuses_invalid_group():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"group": "x\"><script>alert(1)</script>"})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].group != "x\"><script>alert(1)</script>"


def test_patch_refuses_invalid_strategy():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"strategy": "not_a_real_strategy"})
    assert res.status_code == 400


def test_patch_allows_valid_group():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"group": "commodity"})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].group == "commodity"


# ------------------------------------------------------------------- risk bounds

def test_patch_refuses_nan_risk_percent():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", content=b'{"risk_percent": NaN}',
                  headers={"Content-Type": "application/json"})
    assert res.status_code == 400


def test_patch_refuses_max_positions_out_of_range():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"max_positions": 9999})
    assert res.status_code == 400


def test_patch_refuses_nan_in_top_level_exit_field():
    # sl_atr_mult has no per-field bounds entry (unlike risk_percent/max_lot)
    # - the general NaN/Infinity sweep is what has to catch this one.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", content=b'{"sl_atr_mult": NaN}',
                  headers={"Content-Type": "application/json"})
    assert res.status_code == 400
    import math
    assert not math.isnan(store.symbols["XAUUSD"].sl_atr_mult)


def test_patch_refuses_invalid_timeframe():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"timeframe": "M1"})
    assert res.status_code == 400


def test_patch_refuses_invalid_lot_mode():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"lot_mode": "martingale"})
    assert res.status_code == 400


def test_patch_refuses_nan_string_in_top_level_field():
    # The JSON STRING "NaN" (unlike a raw float NaN, this serialises fine)
    # bypassed the old isinstance(value, (int, float)) check entirely and
    # models.py's _coerce() turned it right back into a real NaN via float().
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"sl_atr_mult": "NaN"})
    assert res.status_code == 400


def test_patch_refuses_infinity_string():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"adx_min": "Infinity"})
    assert res.status_code == 400


# ---------------------------------------------------------------- opt/ai params

def test_opt_params_refuses_nan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/opt/params", json={"min_positive_ratio": "NaN"})
    assert res.status_code == 400


def test_ai_settings_refuses_nan():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/ai/settings", json={"watch_pf": "Infinity"})
    assert res.status_code == 400


# ---------------------------------------------------------------- ticket ownership

def test_close_ticket_refuses_position_with_unowned_magic():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 555, "symbol": "XAUUSD", "magic": 123456, "side": "buy"}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/positions/555/close")
    assert res.status_code == 403


def test_close_ticket_allows_owned_position():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 555, "symbol": "XAUUSD", "magic": 990021, "side": "buy",
                  "volume": 0.1}]
    tc, store = _client(symbols, positions)

    res = tc.post("/api/positions/555/close")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_close_ticket_done_partial_returns_ok_false():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    positions = [{"ticket": 556, "symbol": "XAUUSD", "magic": 990021, "side": "buy",
                  "volume": 0.2}]
    store = _FakeStore(symbols)
    client = _FakeClient(positions)
    engine = _FakeEngine()

    def _partial(ticket, slippage, comment, volume=None, fill=None):
        client.closed_tickets.append(int(ticket))
        if fill is not None:
            fill.update({"volume": 0.05, "symbol": "XAUUSD", "side": "buy",
                         "requested": 0.0, "price": 0.0, "risk_dist": 0.0})
        # Leave ticket in book (DONE_PARTIAL)
        for p in client._positions:
            if p["ticket"] == int(ticket):
                p["volume"] = 0.15
        return True

    client.close_position = _partial  # type: ignore[method-assign]
    tc = TestClient(create_app(store, client, engine, optimizer=None))

    res = tc.post("/api/positions/556/close")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert body["partial"] is True
    assert body["remaining_volume"] == 0.15


def test_close_ticket_404s_for_unknown_ticket():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/positions/999/close")
    assert res.status_code == 404


# --------------------------------------------------------------------- API token

def test_api_requires_token_when_configured():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/api/system")
    assert res.status_code == 401


def test_api_accepts_correct_token():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/api/system", headers={"X-Mico-Token": "secret123"})
    assert res.status_code == 200


def test_api_rejects_empty_token_header():
    # L3: secrets.compare_digest requires a real string on both sides - an
    # empty header must still 401 cleanly, not raise/500.
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/api/system", headers={"X-Mico-Token": ""})
    assert res.status_code == 401


def test_api_rejects_wrong_length_token():
    # L3: compare_digest must not blow up (or misbehave) on a candidate
    # shorter/longer than the real token.
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/api/system", headers={"X-Mico-Token": "short"})
    assert res.status_code == 401

    res = tc.get("/api/system", headers={"X-Mico-Token": "secret123-and-then-some-more"})
    assert res.status_code == 401


def test_index_page_requires_token_when_configured():
    # B4: "/" used to be left out of the gate entirely, so the token embedded
    # in its own (then-unauthenticated) HTML was readable by anyone who could
    # reach the port at all - the exact population a non-localhost bind's
    # token exists to keep out. Must 401 with no credentials.
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/")
    assert res.status_code == 401
    assert "secret123" not in res.text


def test_index_page_embeds_token_with_query_param():
    # A plain browser navigation cannot set a custom header, so the token
    # gate on "/" accepts it as a query param too.
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/?token=secret123")
    assert res.status_code == 200
    assert "secret123" in res.text


def test_index_page_embeds_token_with_header():
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/", headers={"X-Mico-Token": "secret123"})
    assert res.status_code == 200
    assert "secret123" in res.text


def test_index_page_rejects_wrong_token():
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/?token=wrong")
    assert res.status_code == 401
    assert "secret123" not in res.text


def test_logs_download_requires_token_when_configured():
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/api/logs/download")
    assert res.status_code == 401


def test_logs_download_accepts_query_param_token():
    # M6: a plain <a href> download link cannot set a custom header - the
    # gate special-cases this one GET route to also accept ?token=, which is
    # what app.js's download link relies on.
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/api/logs/download?token=secret123")
    assert res.status_code != 401  # 404 (no log file yet) is fine - just not auth-rejected


def test_other_api_routes_reject_query_param_token():
    # L3: ?token= is intentionally narrow - only "/" and the log download
    # link need it (a plain browser navigation can't set a header). Every
    # other /api/* route goes through app.js's fetch-based api() helper,
    # which already sets X-Mico-Token - accepting a query param there too
    # would just widen where the token can leak (proxy logs, browser
    # history, an outbound Referer) for no usability gain.
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/api/system?token=secret123")
    assert res.status_code == 401


def test_other_api_routes_still_accept_header_token():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app)

    res = tc.get("/api/system", headers={"X-Mico-Token": "secret123"})
    assert res.status_code == 200
