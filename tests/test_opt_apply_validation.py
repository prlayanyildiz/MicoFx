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

import pytest
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
        "params": {"sl_atr_mult": "NaN", "trail_step_atr": 2.0},
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
        "params": {"sl_atr_mult": 1.5, "trail_step_atr": 0.8, "trail_mode": "atr"},
        "strategy": "t3_stoch", "timeframe": "M15",
    })
    assert res.status_code == 200
    assert len(optimizer.calls) == 1


@pytest.mark.parametrize("params", [
    # The one that actually costs money silently: `if trail_start_atr > 0`
    # gates the trail in both the engine and the simulator, so a 0 here does
    # not mean "arm immediately" - it means the trail NEVER arms and the
    # position runs on its hard stop alone for its whole life. See
    # test_trail_breakeven_invariant.test_trail_start_zero_disables_the_trail.
    {"trail_start_atr": 0.0, "sl_atr_mult": 1.5},
    {"trail_step_atr": 0.0, "sl_atr_mult": 1.5},
    # Hard stop collapsed onto the broker's minimum distance.
    {"sl_atr_mult": 0.0},
    # Negatives: sl_atr_mult < 0 loses the ATR stop entirely, and a negative
    # trail_step_atr puts the trail target on the WRONG side of price.
    {"sl_atr_mult": -5.0},
    {"trail_step_atr": -3.0, "sl_atr_mult": 1.5},
    # Absurd but finite - the finite/enum checks let it straight through.
    {"sl_atr_mult": 9999.0},
])
def test_opt_apply_enforces_the_same_risk_bounds_as_patch(params):
    """The bounds guarded PATCH /api/symbols/{symbol} and only that door.

    OPT_FIELDS carries sl_atr_mult/trail_start_atr/trail_step_atr, so this
    endpoint's hand-typed path wrote the very values _SYMBOL_RISK_BOUNDS
    exists to refuse into the same SymbolConfig, unchecked.
    """
    tc, optimizer = _client()
    res = tc.post("/api/opt/apply", json={"symbol": "XAUUSD", "params": params})
    assert res.status_code == 400, f"{params} was accepted"
    assert optimizer.calls == []

    # ...and the guarded door still refuses them, so the two agree.
    assert tc.post("/api/symbols/XAUUSD", json=params).status_code == 400


def test_opt_apply_run_id_path_risk_bounds_also_enforced():
    """Stored history is not a trusted source for these three either."""
    class _StoreWithHistory(_FakeStore):
        def opt_history(self, symbol, limit):
            return [{"id": 11, "symbol": symbol,
                     "params": {"sl_atr_mult": 1.5, "trail_start_atr": 0.0},
                     "score": 1.0, "timeframe": "M15", "strategy": "t3_stoch",
                     "validated": True}]

    optimizer = _FakeOptimizer()
    store = _StoreWithHistory({"XAUUSD": _cfg("XAUUSD", magic=990021)})
    tc = TestClient(create_app(store, _FakeClient(), _FakeEngine(), optimizer))

    res = tc.post("/api/opt/apply", json={"symbol": "XAUUSD", "run_id": 11})
    assert res.status_code == 400
    assert optimizer.calls == []


def test_opt_apply_still_accepts_the_shipped_grid_range():
    """The fix must not narrow what a real optimizer run can propose."""
    from micofx.paths import load_defaults

    grid = load_defaults()["optimizer"]["grid"]
    tc, optimizer = _client()
    for sl in grid["sl_atr_mult"]:
        for start in grid["trail_start_atr"]:
            for step in grid["trail_step_atr"]:
                res = tc.post("/api/opt/apply", json={
                    "symbol": "XAUUSD",
                    "params": {"sl_atr_mult": sl, "trail_start_atr": start,
                               "trail_step_atr": step},
                })
                assert res.status_code == 200, f"grid value rejected: {sl}/{start}/{step}"
    assert optimizer.calls


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
