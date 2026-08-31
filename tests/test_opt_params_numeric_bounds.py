"""``max_combos`` and ``refine_rounds`` accepted any finite number.

The audit found the pair unbounded: the allowlist lets an operator POST them
and ``set_opt_params`` only checked ``timeframes``, finiteness and the grid
axes. ``max_combos=1e9`` with ``refine_rounds=1e9`` was accepted and
persisted, and every refine round is charged a full ``max_combos`` sweep
(``sweep_budget``), so one POST could wedge the process that is holding the
live book.

Same class one field over: ``flat_before_close_min`` is symbol-writable with
no entry in the risk table (the panel's ``max: 240`` is UI-only, so it is not
a bound), and ``10**9`` there blocks entries on that symbol forever.
``backup_keep`` is system-writable the same way.

The mechanism already exists - these fields just were not in the tables.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

from micofx.models import SymbolConfig
from micofx.web.app import create_app

HEAD = {"Origin": "http://testserver"}


class _System:
    slippage_points = 20
    mt5_terminal_path = ""
    backup_keep = 7

    def to_dict(self):
        return {}


class _Store:
    def __init__(self):
        self.symbols = {"XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1)}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}
        self.saved = None

    def get_setting(self, k, default=None):
        return default

    def opt_params(self):
        return {}

    def save_opt_params(self, body):
        self.saved = body
        return body

    def opt_history(self, s, n):
        return []

    def update_symbol(self, symbol, patch, source=""):
        cfg = self.symbols[symbol]
        for k, v in patch.items():
            setattr(cfg, k, v)
        return cfg

    def update_system(self, patch):
        for k, v in patch.items():
            setattr(self.system, k, v)
        return self.system


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


def _tc(store=None):
    return TestClient(create_app(store or _Store(), _Client(), _Engine(), _Optimizer()))


# ------------------------------------------------------------- the defect

@pytest.mark.parametrize("field,value", [
    ("max_combos", 10 ** 9),
    ("refine_rounds", 10 ** 9),
    ("lookback_days", 10 ** 9),
])
def test_an_absurd_search_budget_is_refused(field, value):
    res = _tc().post("/api/opt/params", json={field: value}, headers=HEAD)
    assert res.status_code == 400, res.text
    assert field in res.text


@pytest.mark.parametrize("field", ["max_combos", "refine_rounds", "lookback_days"])
def test_a_zero_or_negative_search_budget_is_refused(field):
    for value in (0, -1):
        res = _tc().post("/api/opt/params", json={field: value}, headers=HEAD)
        assert res.status_code == 400, f"{field}={value}: {res.text}"


def test_the_search_budget_the_book_actually_runs_is_accepted():
    store = _Store()
    res = _tc(store).post(
        "/api/opt/params",
        json={"max_combos": 2000, "refine_rounds": 5, "lookback_days": 180},
        headers=HEAD,
    )
    assert res.status_code == 200, res.text
    assert store.saved["max_combos"] == 2000


# ------------------------------------------------- the same hole, symbol side

def test_an_absurd_flatten_window_is_refused():
    res = _tc().post("/api/symbols/XAUUSD",
                     json={"flat_before_close_min": 10 ** 9}, headers=HEAD)
    assert res.status_code == 400, res.text
    assert "flat_before_close_min" in res.text


def test_the_flatten_window_the_panel_offers_is_accepted():
    res = _tc().post("/api/symbols/XAUUSD",
                     json={"flat_before_close_min": 30}, headers=HEAD)
    assert res.status_code == 200, res.text


def test_an_absurd_backup_keep_is_refused():
    res = _tc().post("/api/system", json={"backup_keep": 10 ** 9}, headers=HEAD)
    assert res.status_code == 400, res.text
