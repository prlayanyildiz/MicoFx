"""Empty patch returned ok:true and bulk incremented changed with no
real edit. Found 15.08 after 76eaebe: {} and {patch:{}} still succeeded;
bulk rewrote every symbol and counted them. The apply-or-reject rule
must not have an empty-patch exception.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _System:
    slippage_points = 20

    def to_dict(self):
        return {}


class _Store:
    def __init__(self):
        cfg = SymbolConfig(symbol="XAUUSD", magic=1, enabled=False)
        cfg.opt_updated_at = time.time()
        self.symbols = {"XAUUSD": cfg}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}
        self.writes = 0

    def get_setting(self, k, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, s, n):
        return []

    def update_symbol(self, symbol, patch, source=""):
        self.writes += 1
        cur = self.symbols[symbol].to_dict()
        for k, v in patch.items():
            if k in cur and v is not None:
                cur[k] = v
        self.symbols[symbol] = SymbolConfig.from_dict(cur)
        return self.symbols[symbol]


class _Cli:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None


class _Eng:
    def __init__(self):
        self.entry_lock = threading.Lock()
        self.states = {}
        self._sec_cfgs = {}


class _Opt:
    MAX_COST_PER_TRADE_R = 0.25

    def _spread_scale(self, s):
        return 1.0


def _tc():
    return TestClient(create_app(_Store(), _Cli(), _Eng(), _Opt())), None


def test_empty_body_is_400():
    store = _Store()
    tc = TestClient(create_app(store, _Cli(), _Eng(), _Opt()))
    res = tc.post("/api/symbols/XAUUSD", json={})
    assert res.status_code == 400, res.text
    assert store.writes == 0


def test_empty_nested_patch_is_400():
    store = _Store()
    tc = TestClient(create_app(store, _Cli(), _Eng(), _Opt()))
    res = tc.post("/api/symbols/XAUUSD", json={"patch": {}})
    assert res.status_code == 400, res.text
    assert store.writes == 0


def test_empty_bulk_patch_is_400():
    store = _Store()
    tc = TestClient(create_app(store, _Cli(), _Eng(), _Opt()))
    res = tc.post("/api/symbols-bulk", json={"patch": {}})
    assert res.status_code == 400, res.text
    assert store.writes == 0


def test_bulk_changed_counts_only_real_diffs():
    store = _Store()
    tc = TestClient(create_app(store, _Cli(), _Eng(), _Opt()))
    same = tc.post("/api/symbols-bulk", json={"patch": {"enabled": False}})
    assert same.status_code == 200, same.text
    assert same.json()["changed"] == 0
    flip = tc.post("/api/symbols-bulk", json={"patch": {"enabled": True}})
    assert flip.status_code == 200, flip.text
    assert flip.json()["changed"] == 1
    assert store.symbols["XAUUSD"].enabled is True
