"""Open tickets must block session / use_sessions PATCH (Claude TEYIT Py #3).

09-04 XAU #325114801: use_sessions flipped True while ticket open, then 10018.
clock_changed only restamped holdout; it was not in the open-position guard set.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig, SystemConfig
from micofx.web.app import create_app

HEAD = {"Origin": "http://testserver"}


class _Store:
    def __init__(self):
        self.system = SystemConfig()
        self.defaults = {"symbols": [], "group_presets": {}}
        self.symbols = {
            "XAUUSD": SymbolConfig(
                symbol="XAUUSD", magic=990021, enabled=True,
                strategy="mtf_pullback", timeframe="M15",
                use_sessions=False,
                sessions=[{"start": "01:01", "end": "23:59"}],
                opt_updated_at=1.0, opt_score=1.0, validated=True,
            ),
        }

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch, source=""):
        cfg = self.symbols[symbol]
        for key, value in patch.items():
            setattr(cfg, key, value)
        return cfg


class _Client:
    connected = True

    def __init__(self, positions=None):
        self._positions = list(positions or [])

    def positions(self, magic=None, symbol=None):
        rows = self._positions
        if magic is not None:
            rows = [p for p in rows if p.get("magic") == magic]
        return rows

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return {"name": symbol, "volume_min": 0.01, "volume_step": 0.01,
                "digits": 2, "description": symbol}


class _Engine:
    entry_lock = threading.Lock()

    def refresh_account(self, force=False):
        return {}


def test_use_sessions_patch_409_while_ticket_open():
    store = _Store()
    client = _Client([{"ticket": 325114801, "symbol": "XAUUSD", "magic": 990021}])
    app = create_app(store, client, _Engine(), optimizer=None)
    tc = TestClient(app)
    res = tc.post(
        "/api/symbols/XAUUSD",
        json={"use_sessions": True},
        headers=HEAD,
    )
    assert res.status_code == 409, res.text
    assert "seans" in res.json()["detail"].lower()
    assert store.symbols["XAUUSD"].use_sessions is False


def test_sessions_patch_409_while_ticket_open():
    store = _Store()
    store.symbols["XAUUSD"].use_sessions = True
    client = _Client([{"ticket": 1, "symbol": "XAUUSD", "magic": 990021}])
    app = create_app(store, client, _Engine(), optimizer=None)
    tc = TestClient(app)
    res = tc.post(
        "/api/symbols/XAUUSD",
        json={"sessions": [{"start": "15:00", "end": "21:00"}]},
        headers=HEAD,
    )
    assert res.status_code == 409, res.text
    assert store.symbols["XAUUSD"].sessions[0]["start"] == "01:01"


def test_sessions_patch_ok_when_flat():
    store = _Store()
    store.symbols["XAUUSD"].use_sessions = True
    app = create_app(store, _Client([]), _Engine(), optimizer=None)
    tc = TestClient(app)
    res = tc.post(
        "/api/symbols/XAUUSD",
        json={"sessions": [{"start": "15:00", "end": "21:00"}]},
        headers=HEAD,
    )
    assert res.status_code == 200, res.text
    assert store.symbols["XAUUSD"].sessions[0]["start"] == "15:00"
