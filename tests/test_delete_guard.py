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

    def deals_since(self, ts):
        # Closed-deal history. Settable per test; empty means "no magic in
        # this window has traded today", which is the ordinary case.
        return list(getattr(self, "deals", []))

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
    def forget(self, symbol):
        self.cleared.append(symbol) if hasattr(self, 'cleared') else None

    def clear(self, symbol):
        pass


class _FakeExecution:
    def drop_symbol(self, symbol):
        pass


class _FakeEngine:
    def forget_filled_bars(self, symbol):
        pass

    def forget_spread_ratio(self, symbol):
        pass

    def forget_entry_blocks(self, symbol):
        pass

    def __init__(self):
        self.states = {}
        self.supervisor = _FakeSupervisor()
        self.execution = _FakeExecution()
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}

    def _day_start_epoch(self):
        # Real Engine derives this from the day anchor; the magic guard only
        # needs a window start, and these tests carry no deal history.
        return 0.0


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


def test_patch_ignores_retired_secondary_identity_field():
    """Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok."""
    symbols = {"XAUUSD": SymbolConfig(symbol="XAUUSD", magic=990021)}
    positions = [{"ticket": 100, "symbol": "XAUUSD", "magic": 990021, "side": "buy"}]
    tc, store = _client(symbols, positions, settings={"secondary_tickets": [100]})

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_strategy": "burst"})
    assert res.status_code == 422
    assert not hasattr(store.symbols["XAUUSD"], "secondary_strategy")


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
    assert res.status_code == 422


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


# ----------------------------------------------------- retired nested blob is ignored

def test_patch_ignores_retired_secondary_params_blob():
    """Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok."""
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_params": "wipe"})
    assert res.status_code == 422
    assert not hasattr(store.symbols["XAUUSD"], "secondary_params")


def test_patch_ignores_nan_inside_retired_secondary_params():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_params": {"sl_atr_mult": 1.0}})
    assert res.status_code == 422
    assert not hasattr(store.symbols["XAUUSD"], "secondary_params")


def test_patch_ignores_secondary_params_even_with_open_position():
    symbols = {"XAUUSD": SymbolConfig(symbol="XAUUSD", magic=990021)}
    positions = [{"ticket": 100, "symbol": "XAUUSD", "magic": 990021, "side": "buy"}]
    tc, store = _client(symbols, positions, settings={"secondary_tickets": [100]})

    res = tc.post("/api/symbols/XAUUSD", json={"secondary_params": {"sl_atr_mult": 2.0, "adx_min": 20.0}})
    assert res.status_code == 422
    assert not hasattr(store.symbols["XAUUSD"], "secondary_params")


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


def test_patch_refuses_max_positions_above_the_operator_cap():
    """Operator cap is ten. 11 used to be a silent panel write (bound was 50)."""
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"max_positions": 11})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].max_positions == 1


def test_patch_accepts_max_positions_at_the_operator_cap():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    tc, store = _client(symbols, [])

    res = tc.post("/api/symbols/XAUUSD", json={"max_positions": 10})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].max_positions == 10


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

    # M1 is a real timeframe since 14.08; use one that is genuinely not offered.
    res = tc.post("/api/symbols/XAUUSD", json={"timeframe": "M3"})
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
    tc = TestClient(app, unauth=True)

    res = tc.get("/api/system")
    assert res.status_code == 401


def test_api_accepts_correct_token():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app, unauth=True)

    res = tc.get("/api/system", headers={"X-Mico-Token": "secret123"})
    assert res.status_code == 200


def test_api_rejects_empty_token_header():
    # L3: secrets.compare_digest requires a real string on both sides - an
    # empty header must still 401 cleanly, not raise/500.
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app, unauth=True)

    res = tc.get("/api/system", headers={"X-Mico-Token": ""})
    assert res.status_code == 401


def test_api_rejects_wrong_length_token():
    # L3: compare_digest must not blow up (or misbehave) on a candidate
    # shorter/longer than the real token.
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app, unauth=True)

    res = tc.get("/api/system", headers={"X-Mico-Token": "short"})
    assert res.status_code == 401

    res = tc.get("/api/system", headers={"X-Mico-Token": "secret123-and-then-some-more"})
    assert res.status_code == 401


def test_index_page_bootstraps_without_embedding_the_secret():
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app, unauth=True)

    res = tc.get("/")
    assert res.status_code == 200
    assert "secret123" not in res.text
    assert "mico-api-token" not in res.text


def test_query_param_token_does_not_unlock_the_api():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app, unauth=True)

    res = tc.get("/api/system?token=secret123")
    assert res.status_code == 401
    res = tc.get("/api/logs/download?token=secret123")
    assert res.status_code == 401


def test_logs_download_requires_session():
    store = _FakeStore({})
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app, unauth=True)

    res = tc.get("/api/logs/download")
    assert res.status_code == 401


def test_other_api_routes_still_accept_header_token():
    symbols = {"XAUUSD": _cfg("XAUUSD", magic=990021)}
    store = _FakeStore(symbols)
    client = _FakeClient([])
    engine = _FakeEngine()
    app = create_app(store, client, engine, optimizer=None, api_token="secret123")
    tc = TestClient(app, unauth=True)

    res = tc.get("/api/system", headers={"X-Mico-Token": "secret123"})
    assert res.status_code == 200


# --------------------------------------------------------------- stale magic

def _app_with_deals(symbols, deals):
    store = _FakeStore(symbols)
    client = _FakeClient([])
    client.deals = deals
    app = create_app(store, client, _FakeEngine(), optimizer=None)
    return TestClient(app)


def test_a_magic_that_traded_today_cannot_be_handed_to_another_symbol():
    """Deleting a symbol frees its magic but not its closed deals.

    engine.day_stats() and supervisor.review() both attribute a deal to a
    symbol through its magic, so reassigning a number that already traded
    today books the deleted symbol's wins and losses against the new one - it
    starts the day carrying a P/L and a profit factor it never earned, and the
    supervisor can suspend it on them.
    """
    tc = _app_with_deals(
        {"GER40": _cfg("GER40", magic=990011)},
        deals=[{"magic": 990099, "time": 1786600000, "symbol": "EURUSD",
                "profit": -12.0, "commission": 0.0, "swap": 0.0}])

    r = tc.post("/api/symbols/GER40", json={"magic": 990099})

    assert r.status_code == 409
    assert "990099" in r.json()["detail"]


def test_a_magic_with_no_deals_today_is_still_assignable():
    """The guard is about today's window, not about the number ever existing."""
    tc = _app_with_deals(
        {"GER40": _cfg("GER40", magic=990011)},
        deals=[{"magic": 990077, "time": 1786600000, "symbol": "EURUSD",
                "profit": -12.0, "commission": 0.0, "swap": 0.0}])

    r = tc.post("/api/symbols/GER40", json={"magic": 990099})

    assert r.status_code == 200, r.json()


def test_a_magic_is_not_cleared_while_disconnected():
    """A magic change while disconnected is refused, not guessed at.

    deals_since() answers with an empty list on a dropped connection exactly as
    it does for a genuinely quiet day, so reading it while disconnected could
    hand out a magic that already owns today's trades. Cursor's #075 flagged
    that as an open fail-open; measured, it is not - _require_connected()
    already refuses the whole request upstream with 503, because changing a
    magic is a guarded operation. The check inside the guard stays as a second
    belt for any future caller that does not pass through that gate, but this
    pins the behaviour that actually protects the account today.
    """
    store = _FakeStore({"GER40": _cfg("GER40", magic=990011)})
    client = _FakeClient([])
    client.connected = False
    client.deals = []
    tc = TestClient(create_app(store, client, _FakeEngine(), optimizer=None))

    r = tc.post("/api/symbols/GER40", json={"magic": 990099})

    assert r.status_code == 503, "a magic change must not proceed on unverifiable state"
