"""/api/state must not rebuild symbol_payload (MT5 info) every 3s.

Config rows change on PATCH/add/delete. The 3s poll needs a cheap stamp
so the panel can refetch /api/symbols when the set actually changes.
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
        self.symbols = {
            "GER40": SymbolConfig(symbol="GER40", magic=1, enabled=True,
                                  timeframe="M30", strategy="stoch_flip"),
        }
        self.system = SystemConfig()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, k, default=None):
        return default

    def opt_params(self):
        return {"max_bars": 20000, "segments": 5}

    def opt_history(self, s, n):
        return []


class _Cli:
    connected = True
    last_error = ""
    info_calls = 0

    def set_overrides(self, m):
        pass

    def info(self, symbol):
        type(self).info_calls += 1
        return {"name": symbol, "description": symbol, "digits": 1,
                "volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01,
                "point": 0.1, "tick_value": 1.0, "tick_size": 0.1,
                "trade_mode": 4}


class _Eng:
    def __init__(self):
        self.entry_lock = threading.Lock()
        self.states = {}
        self._sec_cfgs = {}

    def snapshot(self):
        return {"bot": {"running": False}, "account": {}, "positions": [],
                "capacity": {}, "day": {}, "mt5": {"connected": True}}


class _Opt:
    busy = False

    def status(self):
        return {"state": "idle", "busy": False}


def _tc():
    return TestClient(create_app(_Store(), _Cli(), _Eng(), _Opt()))


def test_state_does_not_include_symbol_rows():
    body = _tc().get("/api/state").json()
    assert "symbols" not in body
    assert "symbols_sig" in body
    assert "GER40" in body["symbols_sig"]


def test_symbols_sig_moves_when_params_change_not_only_the_name_set():
    store = _Store()
    store.symbols_rev = 0
    tc = TestClient(create_app(store, _Cli(), _Eng(), _Opt()))
    first = tc.get("/api/state").json()["symbols_sig"]
    store.symbols_rev = 3
    second = tc.get("/api/state").json()["symbols_sig"]
    assert first != second
    assert first.startswith("GER40:")
    assert second.endswith(":3")


def test_state_poll_does_not_call_symbol_info():
    _Cli.info_calls = 0
    _tc().get("/api/state")
    assert _Cli.info_calls == 0


def test_symbols_endpoint_still_serves_rows():
    body = _tc().get("/api/symbols").json()
    assert body["ok"] is True
    assert body["symbols"][0]["symbol"] == "GER40"
