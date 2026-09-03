"""Default WFO bag is M15/M30; M5 stays legal to trade and one-off searchable.

Claude 03.09 M5 costed pre-check (US30_M5 −24..−295 vs M30 +43) reconfirmed the
28.08 drop: M5 spread vs target kills edge on tested names. Full 6-symbol M5
snapshot comparison may reopen the bag; until then the shipped default stays
M15/M30. ``POST /api/opt/params`` or a one-off ``POST /api/opt/run`` can still
name M5.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SEARCH_TIMEFRAMES, TIMEFRAMES, SymbolConfig, SystemConfig
from micofx.web.app import create_app


def test_m5_remains_a_legal_bar_but_not_default_search():
    assert "M5" in TIMEFRAMES
    assert SEARCH_TIMEFRAMES == ["M15", "M30"]
    assert "M5" not in SEARCH_TIMEFRAMES


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


def test_opt_params_post_writes_the_search_bag():
    tc, store = _client()
    res = tc.post("/api/opt/params", json={"timeframes": ["M15", "M30"]})
    assert res.status_code == 200, res.text
    assert store.saved_opt["timeframes"] == ["M15", "M30"]


def test_opt_params_post_refuses_an_empty_or_dead_bag():
    tc, store = _client()
    assert tc.post("/api/opt/params", json={"timeframes": []}).status_code == 400
    assert tc.post("/api/opt/params", json={"timeframes": ["H1"]}).status_code == 400
    assert store.saved_opt is None


def test_opt_params_post_can_put_m5_back():
    """One-off persist is still legal after a full 6-symbol M5 proof."""
    tc, store = _client()
    res = tc.post("/api/opt/params", json={"timeframes": ["M5", "M15", "M30"]})
    assert res.status_code == 200, res.text
    assert store.saved_opt["timeframes"] == ["M5", "M15", "M30"]
