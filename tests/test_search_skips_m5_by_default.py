"""Default WFO bag is M5/M15/M30; operator vision 03.09 restores M5.

Overnight 28.08 dropped M5 from the default bag (bar-fetch cost + weak Brent
stamps). Operator 03.09 wants WFO to evaluate M5/M15/M30 and keep only what
beats — M5 stays selectable, not forced. A narrower POST /api/opt/params bag
or a one-off POST /api/opt/run strategies/timeframes subset is still legal.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SEARCH_TIMEFRAMES, TIMEFRAMES, SymbolConfig, SystemConfig
from micofx.web.app import create_app


def test_m5_is_in_the_default_search_bag():
    assert "M5" in TIMEFRAMES
    assert SEARCH_TIMEFRAMES == ["M5", "M15", "M30"]


def test_shipped_search_bag_matches_search_timeframes():
    defaults = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "defaults.json")
        .read_text(encoding="utf-8"))
    assert defaults["optimizer"]["timeframes"] == SEARCH_TIMEFRAMES


def test_empty_opt_blob_does_not_fall_back_to_m5_only():
    src = (Path(__file__).resolve().parents[1] / "micofx" / "optimizer.py").read_text(
        encoding="utf-8")
    assert "or SEARCH_TIMEFRAMES" in src
    assert 'or ["M5"]' not in src.split("timeframes =", 1)[1][:400]

class _Store:
    def __init__(self):
        self.system = SystemConfig()
        self.symbols = {
            "XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1, enabled=False),
        }
        self.defaults = {"symbols": [], "group_presets": {}}
        self.saved_opt = None

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def save_opt_params(self, params):
        self.saved_opt = params
        return params

    def update_system(self, patch, source=""):
        return self.system

    def update_symbol(self, symbol, patch, source=""):
        return self.symbols[symbol]


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
        self.supervisor = None


def _client():
    store = _Store()
    app = create_app(store, _Client(), _Engine(), optimizer=None)
    return TestClient(app), store


def test_opt_params_post_writes_the_full_search_bag():
    tc, store = _client()
    res = tc.post("/api/opt/params", json={"timeframes": ["M5", "M15", "M30"]})
    assert res.status_code == 200, res.text
    assert store.saved_opt["timeframes"] == ["M5", "M15", "M30"]


def test_opt_params_post_refuses_an_empty_or_dead_bag():
    tc, store = _client()
    assert tc.post("/api/opt/params", json={"timeframes": []}).status_code == 400
    assert tc.post("/api/opt/params", json={"timeframes": ["H1"]}).status_code == 400
    assert store.saved_opt is None


def test_opt_params_post_can_narrow_away_from_m5():
    """Persist may still drop M5; default shipped bag is what restored it."""
    tc, store = _client()
    res = tc.post("/api/opt/params", json={"timeframes": ["M15", "M30"]})
    assert res.status_code == 200, res.text
    assert store.saved_opt["timeframes"] == ["M15", "M30"]
