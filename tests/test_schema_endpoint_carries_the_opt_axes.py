"""The OPT-axis catalogue moved off /api/state onto its own endpoint.

`opt_fields`, `engine_opt_fields` and `strategy_opt_fields` are built from
module constants, so they cannot change while the process is up - yet they
rode on every /api/state, which the panel polls every ~3s and every 1.5s while
a search runs (2155 bytes and twelve sorted() calls per poll, measured 25.08).

The risk of moving them is silent: `optFieldVisible()` in app.js returns
"show the field" when the catalogue is missing, so a panel reading the old
keys would not error - it would quietly show axes the family never reads, and
nobody would notice until an operator tuned a dead dial. These tests fail
loudly instead: the values must be present on /api/schema, and absent from
/api/state so a stale consumer cannot half-work.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import OPT_FIELDS, SymbolConfig, SystemConfig
from micofx.strategy import _FAMILIES, ENGINE_OPT_FIELDS, opt_fields_read
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

    def set_overrides(self, m):
        pass

    def info(self, symbol):
        # Every key symbol_payload() reads off info(), supplied at once so a
        # missing one does not turn into a KeyError chase.
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
        """Just enough shape for the handler; the real one talks to MT5."""
        return {"bot": {"running": False}, "account": {}, "positions": [],
                "capacity": {}, "day": {}, "mt5": {"connected": True}}


class _Opt:
    busy = False

    def status(self):
        return {"state": "idle", "busy": False}


def _tc():
    return TestClient(create_app(_Store(), _Cli(), _Eng(), _Opt()))


def _get(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, (path, resp.status_code, resp.text)
    return resp.json()


def test_schema_serves_the_three_catalogues():
    body = _get(_tc(), "/api/schema")
    assert body["ok"] is True
    assert body["opt_fields"] == list(OPT_FIELDS)
    assert body["engine_opt_fields"] == sorted(ENGINE_OPT_FIELDS)


def test_every_family_has_its_own_axis_list():
    """A family missing here hides nothing, which is the silent failure."""
    body = _get(_tc(), "/api/schema")
    per_family = body["strategy_opt_fields"]
    assert set(per_family) == set(_FAMILIES)
    for name in _FAMILIES:
        assert per_family[name] == sorted(opt_fields_read(name))


def test_the_catalogues_are_gone_from_state():
    """Absent, not stale. A half-populated /api/state is the worse outcome."""
    body = _get(_tc(), "/api/state")
    for key in ("opt_fields", "engine_opt_fields", "strategy_opt_fields"):
        assert key not in body, f"{key} still rides on /api/state"


def test_state_still_carries_what_the_panel_polls_for():
    """The slimming must not take anything the 3s poll actually needs."""
    body = _get(_tc(), "/api/state")
    for key in ("ok", "ts", "version", "symbols", "system", "opt"):
        assert key in body, f"/api/state lost {key}"


def test_schema_does_not_change_between_calls():
    """Static per process - that is the whole justification for moving it."""
    client = _tc()
    assert _get(client, "/api/schema") == _get(client, "/api/schema")
