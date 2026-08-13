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


# --------------------------------------------------------- exit-model bounds

def test_patch_symbol_rejects_zero_trail_start():
    """0 reads as "arm the trail immediately"; it actually disables the trail.

    engine._update_stop and backtest both arm behind ``if trail_start_atr > 0``,
    so a hand-typed 0 leaves the position running on its hard stop alone for its
    entire life - no ratchet, no breakeven, nothing gives back a winner's gains.
    No shipped grid contains 0, so the optimizer can never produce it; the API
    was the only door and it was open.
    """
    tc, store = _client()
    before = store.symbols["XAUUSD"].trail_start_atr
    res = tc.post("/api/symbols/XAUUSD", json={"trail_start_atr": 0})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].trail_start_atr == before


def test_patch_symbol_rejects_zero_trail_step_and_zero_stop():
    """The other two legs of the exit model are strictly positive too.

    trail_step 0 puts the trailing stop exactly on the close (instant stop-out);
    sl_atr_mult 0 collapses the hard stop to the broker's bare minimum distance
    rather than the ATR-sized risk the position was sized against.
    """
    tc, store = _client()
    for field in ("trail_step_atr", "sl_atr_mult"):
        before = getattr(store.symbols["XAUUSD"], field)
        res = tc.post("/api/symbols/XAUUSD", json={field: 0})
        assert res.status_code == 400, field
        assert getattr(store.symbols["XAUUSD"], field) == before, field


def test_patch_symbol_still_accepts_a_small_positive_trail_start():
    """The gate is "> 0", not a tuning opinion - 0.1 and start<=step stay legal."""
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"trail_start_atr": 0.1,
                                               "trail_step_atr": 1.6})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].trail_start_atr == 0.1
    assert store.symbols["XAUUSD"].trail_step_atr == 1.6


# --------------------------------------------------------------- nested blob

def test_patch_symbol_enforces_the_bounds_inside_secondary_params():
    """secondary_params carries its own copy of the exit model.

    The nested blob already had its own non-finite and enum checks (a
    top-level check never looks inside it); the bounds check was the third
    one that had to be repeated and was not. engine.py builds the secondary
    signal's exit payload straight from this dict, so a 0/negative here drove
    a real position's stop while the identical top-level value was refused.
    """
    for field, bad in (("trail_start_atr", 0.0),   # trail never arms at all
                       ("trail_step_atr", 0.0),
                       ("sl_atr_mult", 0.0),
                       ("sl_atr_mult", -5.0),      # no ATR stop left
                       ("trail_step_atr", -3.0),   # trail target on the wrong side
                       ("sl_atr_mult", 9999.0)):   # finite, so the NaN check let it by
        tc, store = _client()
        before = dict(store.symbols["XAUUSD"].secondary_params)
        res = tc.post("/api/symbols/XAUUSD",
                      json={"secondary_params": {field: bad}})
        assert res.status_code == 400, f"secondary_params.{field}={bad} accepted"
        assert field in res.json()["detail"]
        assert store.symbols["XAUUSD"].secondary_params == before


def test_bulk_patch_enforces_the_bounds_inside_secondary_params():
    """Bulk is the other door to the same write, across every symbol at once."""
    tc, store = _client()
    before = dict(store.symbols["XAUUSD"].secondary_params)
    res = tc.post("/api/symbols-bulk",
                  json={"patch": {"secondary_params": {"trail_start_atr": 0.0}}})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].secondary_params == before


def test_valid_secondary_params_still_go_through():
    """The gate is the bounds, not "nested values are suspicious"."""
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={
        "secondary_params": {"sl_atr_mult": 1.5, "trail_start_atr": 0.5,
                             "trail_step_atr": 1.6, "trail_mode": "atr"}})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].secondary_params["sl_atr_mult"] == 1.5
    assert store.symbols["XAUUSD"].secondary_params["trail_start_atr"] == 0.5
