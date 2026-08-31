"""The cost gate could not be searched tight enough to matter.

F49: the live loss concentrates in entry spread/ATR, and it survives a
within-symbol control (cheap half -7.0 R, expensive half -56.1 R, 4 of 5
symbols agreeing). Spread is a *cost*, so the direction is mechanical rather
than a fitted pattern.

The fix was unreachable. ``max_spread_atr`` is an ``OPT_FIELDS`` axis whose
shipped grid floor is 0.05, while the per-symbol medians are 0.013-0.072 - so
for XAUUSD (0.013), NAS100 (0.017) and GER40 (0.031) the *tightest* value the
search could pick already sat above the median. Editing config/defaults.json
does not help either: Store.opt_params merges ``{**shipped, **stored}`` per
axis, so a stored axis keeps its old values forever.

So the opt door opens for cost axes only. Two properties matter:

* everything else in the grid stays hands-off - this is not a general grid
  door, and ``strategy_grids`` is untouched;
* the write **merges**. ``save_opt_params`` does ``base[key] = value``, so
  posting a one-axis grid would otherwise replace the whole shared grid and
  silently delete every other axis.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from micofx.models import SymbolConfig, SystemConfig
from micofx.web.app import create_app


class _Store:
    def __init__(self):
        self.system = SystemConfig()
        self.symbols = {"US30": SymbolConfig(symbol="US30", magic=1)}
        self.defaults = {"symbols": [], "group_presets": {}}
        self.blob = {
            "lookback_days": 365,
            "grid": {
                "max_spread_atr": [0.05, 0.08, 0.12, 0.18, 0.25, 0.4],
                "sl_atr_mult": [1.0, 1.5, 2.0],
            },
            "strategy_grids": {"burst": {"adx_min": [0.0, 15.0]}},
        }

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {k: (dict(v) if isinstance(v, dict) else v)
                for k, v in self.blob.items()}

    def save_opt_params(self, params):
        # Mirrors the real Store: whole-value assignment, no deep merge.
        for key, value in params.items():
            if value is not None:
                self.blob[key] = value
        return self.blob


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return None


class _Engine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


def _client():
    store = _Store()
    app = create_app(store, _Client(), _Engine(), optimizer=None)
    return TestClient(app), store


def test_the_cost_axis_can_be_tightened():
    tc, store = _client()
    tight = [0.01, 0.02, 0.03, 0.05, 0.08, 0.15]
    res = tc.post("/api/opt/params", json={"grid": {"max_spread_atr": tight}})
    assert res.status_code == 200, res.text
    assert store.blob["grid"]["max_spread_atr"] == tight


def test_the_write_merges_instead_of_replacing_the_grid():
    """save_opt_params assigns the whole value - a one-axis post must not wipe."""
    tc, store = _client()
    res = tc.post("/api/opt/params",
                  json={"grid": {"max_spread_atr": [0.01, 0.02]}})
    assert res.status_code == 200, res.text
    assert store.blob["grid"]["sl_atr_mult"] == [1.0, 1.5, 2.0]


def test_a_non_cost_axis_is_still_refused():
    tc, store = _client()
    res = tc.post("/api/opt/params",
                  json={"grid": {"sl_atr_mult": [9.0]}})
    assert res.status_code == 400, res.text
    assert "sl_atr_mult" in res.json()["detail"]
    assert store.blob["grid"]["sl_atr_mult"] == [1.0, 1.5, 2.0]


def test_a_mixed_grid_is_refused_whole():
    """One bad axis must not let the good half through."""
    tc, store = _client()
    res = tc.post("/api/opt/params", json={"grid": {
        "max_spread_atr": [0.01], "sl_atr_mult": [9.0]}})
    assert res.status_code == 400, res.text
    assert store.blob["grid"]["max_spread_atr"] == [0.05, 0.08, 0.12, 0.18,
                                                    0.25, 0.4]


def test_a_poisoned_cost_value_is_refused():
    """These axes are entry gates, so invalid_exit_param never sees them.

    Without a check here a negative or non-finite ceiling would ride the open
    half of the door straight into a sweep.
    """
    tc, store = _client()
    original = list(store.blob["grid"]["max_spread_atr"])
    for bad in ([-0.01], [], ["0.02"], [True], "0.02"):
        res = tc.post("/api/opt/params", json={"grid": {"max_spread_atr": bad}})
        assert res.status_code == 400, f"{bad!r} gecti: {res.text}"
        assert store.blob["grid"]["max_spread_atr"] == original


def test_a_non_finite_ceiling_is_refused():
    """NaN/inf cannot cross JSON, so this guard is checked where it can bite.

    Reachable from any in-process caller of the helper, and cheap insurance if
    a future client hands the endpoint an already-parsed body.
    """
    from fastapi import HTTPException

    from micofx.web.app import _cost_axis_grid

    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(HTTPException) as caught:
            _cost_axis_grid({"grid": {"max_spread_atr": [0.02, bad]}}, {})
        assert caught.value.status_code == 400


def test_per_family_grids_stay_shut():
    tc, store = _client()
    res = tc.post("/api/opt/params",
                  json={"strategy_grids": {"burst": {"adx_min": [0.0]}}})
    assert res.status_code == 400, res.text
    assert store.blob["strategy_grids"]["burst"]["adx_min"] == [0.0, 15.0]


def test_zero_stays_a_legal_value_on_this_axis():
    """0 means "gate off" here, not "invalid".

    Unlike the exit axes, ``max_spread_atr`` documents 0 as disabling the gate
    and the shipped default grid in models.py already carries it. The door does
    not get to redefine the axis; refusing 0 would make this endpoint stricter
    than the search that writes the same field.
    """
    tc, store = _client()
    res = tc.post("/api/opt/params",
                  json={"grid": {"max_spread_atr": [0.0, 0.02]}})
    assert res.status_code == 200, res.text
    assert store.blob["grid"]["max_spread_atr"] == [0.0, 0.02]
