"""POST /api/symbols/{symbol} accepted {\"patch\": {\"enabled\": false}} with
ok:true and left enabled true. Found 15.08 when Claude toggled BTCUSD via
the bulk-shaped body on the single-symbol door; the panel's flat body works
because app.js sends {enabled: false} directly.

A nested ``patch`` key is not a SymbolConfig field, so store.update_symbol
skips it. Same silent drop for any unknown key. The yama must apply or 400.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _System:
    slippage_points = 20

    def to_dict(self):
        return {}


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, k, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, s, n):
        return []

    def update_symbol(self, symbol, patch, source=""):
        cur = self.symbols[symbol].to_dict()
        for k, v in patch.items():
            if k in cur and v is not None:
                cur[k] = v
        self.symbols[symbol] = SymbolConfig.from_dict(cur)
        return self.symbols[symbol]


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None

    def resolve(self, s):
        return s

    def tick(self, s):
        return None


class _Engine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25

    def apply(self, *a, **k):
        return {"ok": True}


def _cfg(symbol, *, enabled=True):
    c = SymbolConfig(symbol=symbol, magic=1, enabled=enabled)
    c.opt_updated_at = time.time()
    c.opt_score = 12.3
    return c


def _client(cfgs):
    store = _Store(cfgs)
    return TestClient(create_app(store, _Client(), _Engine(), _Optimizer())), store


def test_nested_patch_enabled_false_must_disable_the_symbol():
    tc, store = _client([_cfg("BTCUSD", enabled=True)])
    res = tc.post("/api/symbols/BTCUSD", json={"patch": {"enabled": False}})
    assert res.status_code == 200, res.text
    assert res.json()["ok"] is True
    assert res.json()["config"]["enabled"] is False
    assert store.symbols["BTCUSD"].enabled is False


def test_flat_enabled_false_still_disables():
    tc, store = _client([_cfg("BTCUSD", enabled=True)])
    res = tc.post("/api/symbols/BTCUSD", json={"enabled": False})
    assert res.status_code == 200, res.text
    assert store.symbols["BTCUSD"].enabled is False


def test_unknown_field_is_rejected_not_ok_true():
    tc, store = _client([_cfg("BTCUSD", enabled=True)])
    res = tc.post("/api/symbols/BTCUSD", json={"not_a_config_field": 1})
    assert res.status_code == 422, res.text
    assert store.symbols["BTCUSD"].enabled is True
