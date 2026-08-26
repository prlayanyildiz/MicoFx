"""A session cookie must not be able to POST a 10k-name strategies list.

Unknown names already drop against STRATEGIES; the bound stops the
request from becoming an unbounded log line / parse cost.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _System:
    slippage_points = 20
    mt5_terminal_path = ""

    def to_dict(self):
        return {}


class _Store:
    def __init__(self):
        self.symbols = {"XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1)}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, k, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, s, n):
        return []


class _Client:
    connected = True
    last_error = ""

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None

    def terminal_flags(self):
        return {}


class _Engine:
    def __init__(self):
        self.entry_lock = threading.Lock()
        self.states = {}
        self._sec_cfgs = {}


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25

    def start(self, *a, **k):
        return {"ok": True}


def _tc():
    return TestClient(create_app(_Store(), _Client(), _Engine(), _Optimizer()))


def test_a_huge_strategies_list_is_422():
    res = _tc().post(
        "/api/opt/run",
        json={"strategies": [f"fam{i}" for i in range(64)], "apply_best": False},
        headers={"Origin": "http://testserver"},
    )
    assert res.status_code == 422, res.text
