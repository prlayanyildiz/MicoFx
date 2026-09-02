"""Shutdown must 409 while this process still has tickets; restart may proceed.

21:20 / 21:43 / ~21:59 restarted with opens and killed the 20:21 search —
first-sight trail was the miss. Operator 02.09: restart with open tickets is
allowed (MT5 keeps fills; track()/open_original_sl reattach). Shutdown and
holdout capture stay refused. MT5 down still allows restart so a wedged bind
can recover.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _Store:
    def __init__(self):
        self.symbols = {"GER40": SymbolConfig(symbol="GER40", magic=1)}
        self.system = type("S", (), {"to_dict": lambda self: {}})()
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

    def __init__(self, positions=None):
        self._pos = list(positions or [])
        self.killed = False

    def positions(self, magic=None, symbol=None):
        out = self._pos
        if magic is not None:
            out = [p for p in out if p["magic"] == magic]
        return out

    def set_overrides(self, m):
        pass

    def shutdown(self):
        self.killed = True


class _Engine:
    def __init__(self):
        self.entry_lock = threading.Lock()
        self.states = {}
        self._sec_cfgs = {}
        self.stopped = False

    def shutdown(self):
        self.stopped = True


class _Opt:
    busy = False

    def cancel(self):
        return {"ok": True}

    def status(self):
        return {"state": "idle", "busy": False}


def _post(path, client, monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setattr("micofx.web.app.subprocess.Popen", lambda *a, **k: None)
        monkeypatch.setattr("micofx.web.app.os.kill", lambda *a, **k: None)
        monkeypatch.setattr("micofx.web.app.time.sleep", lambda s: None)
    tc = TestClient(create_app(_Store(), client, _Engine(), _Opt()))
    tc.get("/")
    return tc.post(path, headers={"Origin": "http://testserver"})


def test_restart_proceeds_while_a_bot_ticket_is_open(monkeypatch):
    client = _Client([{"ticket": 9, "magic": 1, "symbol": "GER40"}])
    res = _post("/api/app/restart", client, monkeypatch)
    assert res.status_code == 200
    assert res.json()["ok"] is True
    # Thread still runs shutdown after the response; give it a tick.
    import time
    time.sleep(0.05)
    assert client.killed is True


def test_shutdown_is_409_while_a_bot_ticket_is_open(monkeypatch):
    client = _Client([{"ticket": 9, "magic": 1, "symbol": "GER40"}])
    res = _post("/api/app/shutdown", client, monkeypatch)
    assert res.status_code == 409
    assert client.killed is False
