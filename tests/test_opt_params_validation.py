"""POST /api/opt/params - nested NaN/Infinity rejection (M3).

strategy_grids/grid nest their numeric search axes two levels deep
({strategy: {param: [values...]}}), so the flat top-level-only NaN check used
elsewhere would walk right past one buried in a grid list. This drives the
walk-forward search that ultimately writes live trading params via apply().
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.web.app import create_app


class _FakeStore:
    def __init__(self):
        self.symbols: dict = {}
        self.saved = None

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def save_opt_params(self, params):
        self.saved = params
        return params


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


def _client():
    store = _FakeStore()
    app = create_app(store, _FakeClient(), _FakeEngine(), optimizer=None)
    return TestClient(app), store


def test_opt_params_rejects_nan_in_strategy_grids():
    tc, store = _client()
    res = tc.post("/api/opt/params", json={
        "strategy_grids": {"t3_stoch": {"sl_atr_mult": [1.0, 1.2, "NaN", 2.0]}},
    })
    assert res.status_code == 400
    assert store.saved is None


def test_opt_params_rejects_infinity_in_grid():
    tc, store = _client()
    res = tc.post("/api/opt/params", json={
        "grid": {"trail_start_atr": [0.5, "Infinity"]},
    })
    assert res.status_code == 400
    assert store.saved is None


def test_opt_params_rejects_top_level_nan_too():
    tc, store = _client()
    res = tc.post("/api/opt/params", json={"min_trades": "NaN"})
    assert res.status_code == 400
    assert store.saved is None


def test_opt_params_accepts_valid_nested_grids():
    tc, store = _client()
    res = tc.post("/api/opt/params", json={
        "strategy_grids": {"t3_stoch": {"sl_atr_mult": [1.0, 1.2, 1.5]}},
        "grid": {"trail_start_atr": [0.5, 0.8, 1.0]},
        "min_trades": 20,
    })
    assert res.status_code == 200
    assert store.saved is not None


# ------------------------------------------------- RecursionError / depth

def _deep(depth: int) -> dict:
    body: dict = {}
    cur = body
    for _ in range(depth):
        cur["g"] = {}
        cur = cur["g"]
    cur["x"] = 1.0
    return body


def test_a_deeply_nested_body_is_refused_not_a_recursion_error():
    """_reject_non_finite_deep walks a client-supplied body recursively.

    Python's recursion limit is ~1000 frames, so a deep enough payload used to
    raise RecursionError inside the handler - an opaque 500 rather than a
    message saying what was wrong with the request.
    """
    from fastapi import HTTPException

    from micofx.web.app import _reject_non_finite_deep

    with pytest.raises(HTTPException) as err:
        _reject_non_finite_deep(_deep(5000))
    assert err.value.status_code == 400
    assert "ic ice" in err.value.detail


def test_realistic_nesting_still_passes():
    """The real shape is {strategy: {param: [values]}} - three levels."""
    from micofx.web.app import _reject_non_finite_deep

    _reject_non_finite_deep({"strategy_grids": {"orb": {"sl_atr_mult": [1.0, 2.0]}},
                             "grid": {"trail_step_atr": [0.8]}})
    _reject_non_finite_deep(_deep(50))      # comfortably under the cap


def test_the_nan_check_still_fires_inside_nesting():
    """The cap must not shadow what the function is actually for."""
    from fastapi import HTTPException

    from micofx.web.app import _reject_non_finite_deep

    with pytest.raises(HTTPException) as err:
        _reject_non_finite_deep({"grid": {"sl_atr_mult": [1.0, "NaN"]}})
    assert "sl_atr_mult" in err.value.detail
