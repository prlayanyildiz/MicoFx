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


def test_patch_symbol_accepts_zero_breakeven_and_one_point_five():
    """0 disables the lock; 1.5 is the live threshold. Both must pass the door."""
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"breakeven_at_r": 0})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].breakeven_at_r == 0.0
    res = tc.post("/api/symbols/XAUUSD", json={"breakeven_at_r": 1.5})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].breakeven_at_r == 1.5


def test_patch_symbol_rejects_negative_and_oversize_breakeven():
    tc, store = _client()
    before = store.symbols["XAUUSD"].breakeven_at_r
    for value in (-0.5, 5.1):
        res = tc.post("/api/symbols/XAUUSD", json={"breakeven_at_r": value})
        assert res.status_code == 400, value
        assert store.symbols["XAUUSD"].breakeven_at_r == before


# --------------------------------------------------------------- nested blob

def test_patch_symbol_ignores_retired_secondary_params():
    """Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok."""
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD",
                  json={"secondary_params": {"trail_start_atr": 0.0}})
    assert res.status_code == 422
    assert not hasattr(store.symbols["XAUUSD"], "secondary_params")


def test_bulk_patch_ignores_retired_secondary_params():
    tc, store = _client()
    res = tc.post("/api/symbols-bulk",
                  json={"patch": {"secondary_params": {"trail_start_atr": 0.0}}})
    assert res.status_code == 400
    assert not hasattr(store.symbols["XAUUSD"], "secondary_params")
