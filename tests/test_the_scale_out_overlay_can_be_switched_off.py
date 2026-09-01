"""``partial_at_r`` had an on-ramp and no off-ramp.

The overlay was hand-set to 1.5 on five live symbols on 25.08, through a PATCH
route that has since been removed. Nothing else writes it: it is not in
``OPT_FIELDS`` so ``Optimizer.apply()`` never touches it, it is not in
``EXIT_RISK_FIELDS`` so it never queues in ``pending_exit_patch``, and the
symbol POST door refuses it as hands-off. A field that can be turned on and
never off is not a hands-off field, it is a latch.

It is a costed loser besides (F44): scaling out a third at any rung tested
worse than leaving the position whole on every captured window, worst at the
earliest rung, by lifting win rate while crushing payoff.

So the door opens one way. Turning the overlay OFF mid-trade is monotone - the
partial simply never fires - while turning it ON mid-trade is the documented
25.08 hazard, since a position already past the rung closes a third the
instant the value lands. Only 0 is accepted.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig, SystemConfig
from micofx.web.app import create_app


class _Store:
    def __init__(self):
        self.system = SystemConfig()
        self.symbols = {
            "US30": SymbolConfig(symbol="US30", magic=1, enabled=False,
                                 partial_at_r=1.5),
            "GER40": SymbolConfig(symbol="GER40", magic=2, enabled=False,
                                  partial_at_r=1.5),
        }
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch, source=""):
        cfg = self.symbols[symbol]
        for key, value in patch.items():
            setattr(cfg, key, value)
        return cfg


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


def test_the_overlay_can_be_switched_off():
    tc, store = _client()
    res = tc.post("/api/symbols/US30", json={"partial_at_r": 0.0})
    assert res.status_code == 200, res.text
    assert store.symbols["US30"].partial_at_r == 0.0


def test_the_overlay_cannot_be_switched_on_at_arbitrary_rungs():
    """F44: every rung costed worse than off. No writer turns it back on."""
    tc, store = _client()
    res = tc.post("/api/symbols/US30", json={"partial_at_r": 1.0})
    assert res.status_code == 400, res.text
    assert "partial_at_r" in res.json()["detail"]
    assert store.symbols["US30"].partial_at_r == 1.5


def test_the_overlay_cannot_be_switched_on_at_shipped_rungs():
    """23:58 bulk write turned every symbol to 1.5. POST accepts 0 only."""
    tc, store = _client()
    for rung in (1.5, 2.0, 3.0):
        res = tc.post("/api/symbols/US30", json={"partial_at_r": rung})
        assert res.status_code == 400, (rung, res.text)
        assert store.symbols["US30"].partial_at_r == 1.5


def test_the_bulk_door_agrees_with_the_single_door():
    """Two doors, one rule - the shape this file exists to stop repeating."""
    tc, store = _client()
    res = tc.post("/api/symbols-bulk",
                  json={"symbols": ["US30", "GER40"],
                        "patch": {"partial_at_r": 0.0}})
    assert res.status_code == 200, res.text
    assert store.symbols["US30"].partial_at_r == 0.0
    assert store.symbols["GER40"].partial_at_r == 0.0

    res = tc.post("/api/symbols-bulk",
                  json={"symbols": ["US30"], "patch": {"partial_at_r": 2.0}})
    assert res.status_code == 400, res.text
    assert store.symbols["US30"].partial_at_r == 0.0


def test_the_sibling_overlays_stay_shut():
    """Only the latch opens. harvest is off and measured worse on (F41)."""
    tc, store = _client()
    for key, value in (("harvest_at_r", 1.0), ("harvest_step_atr", 0.5),
                       ("breakeven_at_r", 0.0)):
        res = tc.post("/api/symbols/US30", json={key: value})
        assert res.status_code == 400, (key, res.text)
