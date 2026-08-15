"""The exit model's bounds must hold at every door, including the ones with
no HTTP handler in front of them.

test_symbol_risk_bounds / test_opt_apply_validation cover the request bodies.
This file covers the two paths a request never touches:

- Optimizer.apply(), which the auto-apply path of a search
  run reaches directly. The search grid is user-editable, so a poisoned axis
  could be searched, win on score, and be written straight to a live symbol.
- POST /api/opt/params, which sets that grid - refused at the point it is set,
  while there is a human to read the message, rather than only at the far end.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import invalid_exit_param

BAD = [
    # 0 does not mean "off" for any of the three - see invalid_exit_param.
    ({"trail_start_atr": 0.0}, "trail_start_atr"),
    ({"trail_step_atr": 0.0}, "trail_step_atr"),
    ({"sl_atr_mult": 0.0}, "sl_atr_mult"),
    ({"sl_atr_mult": -5.0}, "sl_atr_mult"),
    ({"trail_step_atr": -3.0}, "trail_step_atr"),
    ({"sl_atr_mult": 9999.0}, "sl_atr_mult"),
    ({"trail_start_atr": float("nan")}, "trail_start_atr"),
]

GOOD = {"sl_atr_mult": 1.5, "trail_start_atr": 0.5, "trail_step_atr": 1.6}


# ------------------------------------------------------------ the validator

@pytest.mark.parametrize("params,field", BAD)
def test_invalid_exit_param_names_the_offending_field(params, field):
    reason = invalid_exit_param(params)
    assert reason, f"{params} passed"
    assert field in reason


def test_invalid_exit_param_passes_a_sane_config():
    assert invalid_exit_param(GOOD) == ""


def test_invalid_exit_param_ignores_fields_it_does_not_own():
    """Only the three exit numbers are checked here; nothing else is touched."""
    assert invalid_exit_param({"adx_min": 0, "t3_length": 0, "rsi_length": 0}) == ""


def test_every_shipped_grid_value_is_accepted():
    """The gate must not narrow what a real search can legitimately propose."""
    from micofx.paths import load_defaults

    opt = load_defaults()["optimizer"]
    grids = [opt.get("grid", {})]
    grids += list((opt.get("strategy_grids") or {}).values())
    checked = 0
    for grid in grids:
        for axis, values in grid.items():
            for value in values:
                assert invalid_exit_param({axis: value}) == "", \
                    f"shipped grid value rejected: {axis}={value}"
                checked += 1
    assert checked, "no grid axes were actually checked"


# --------------------------------------------------- POST /api/opt/params

def _params_client():
    from fastapi.testclient import TestClient
    from test_opt_apply_validation import _cfg, _FakeClient, _FakeEngine, _FakeOptimizer, _FakeStore

    from micofx.web.app import create_app

    class _Store(_FakeStore):
        def __init__(self, symbols):
            super().__init__(symbols)
            self.saved = None

        def save_opt_params(self, body):
            self.saved = body
            return body

    store = _Store({"XAUUSD": _cfg("XAUUSD", magic=990021)})
    app = create_app(store, _FakeClient(), _FakeEngine(), _FakeOptimizer())
    return TestClient(app), store


def test_opt_params_refuses_a_poisoned_shared_grid_axis():
    tc, store = _params_client()
    res = tc.post("/api/opt/params", json={"grid": {"trail_start_atr": [0.0, 0.5]}})
    assert res.status_code == 400
    assert "trail_start_atr" in res.json()["detail"]
    assert store.saved is None


def test_opt_params_refuses_a_poisoned_per_strategy_grid_axis():
    """strategy_grids overrides the shared grid, so it is the same door."""
    tc, store = _params_client()
    res = tc.post("/api/opt/params",
                  json={"strategy_grids": {"orb": {"trail_step_atr": [0.0]}}})
    assert res.status_code == 400
    assert store.saved is None


def test_opt_params_still_accepts_a_valid_grid():
    tc, store = _params_client()
    res = tc.post("/api/opt/params", json={
        "grid": {"trail_start_atr": [0.3, 0.5], "sl_atr_mult": [1.0, 2.0],
                 "trail_step_atr": [0.8, 1.6]},
        "max_combos": 2000,
    })
    assert res.status_code == 200
    assert store.saved is not None


def test_opt_params_leaves_non_exit_axes_alone():
    """adx_min 0 is a legitimate grid value; the gate owns three fields only."""
    tc, store = _params_client()
    res = tc.post("/api/opt/params", json={"grid": {"adx_min": [0, 15, 25]}})
    assert res.status_code == 200
    assert store.saved is not None
