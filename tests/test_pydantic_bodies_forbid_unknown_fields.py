"""Pydantic request bodies used extra=allow / default-ignore, so a typo or
the bulk envelope on the wrong door returned ok:true and changed nothing.
Found 15.08 on POST /api/symbols/BTCUSD {\"patch\": {\"enabled\": false}}.
Unknown keys must 422 at the model, not be swallowed.
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
    backup_dir_allow_unc = False

    def to_dict(self):
        return {}


class _Store:
    def __init__(self):
        cfg = SymbolConfig(symbol="XAUUSD", magic=1, enabled=True)
        cfg.opt_updated_at = time.time()
        self.symbols = {"XAUUSD": cfg}
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

    def update_system(self, patch, source=""):
        return self.system

    def add_symbol(self, symbol, **kw):
        cfg = SymbolConfig(symbol=symbol, magic=2, **{k: v for k, v in kw.items()
                           if k in SymbolConfig.__dataclass_fields__})
        self.symbols[symbol] = cfg
        return cfg


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


def _tc():
    return TestClient(create_app(_Store(), _Client(), _Engine(), _Optimizer()))


def test_symbol_patch_unknown_field_is_422():
    res = _tc().post("/api/symbols/XAUUSD", json={"not_a_config_field": 1})
    assert res.status_code == 422, res.text


def test_symbol_create_unknown_field_is_422():
    res = _tc().post("/api/symbols", json={"symbol": "FOO", "typo_group": "forex"})
    assert res.status_code == 422, res.text


def test_system_patch_unknown_field_is_422():
    res = _tc().post("/api/system", json={"not_a_system_field": True})
    assert res.status_code == 422, res.text


def test_opt_run_unknown_field_is_422():
    res = _tc().post("/api/opt/run", json={"nope": 1},
                     headers={"Origin": "http://testserver"})
    assert res.status_code == 422, res.text


def test_bulk_patch_unknown_top_level_is_422():
    res = _tc().post("/api/symbols-bulk", json={"patch": {"enabled": False}, "typo": 1})
    assert res.status_code == 422, res.text
