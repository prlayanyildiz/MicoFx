"""Refuse soft-restart while a search is running (Claude 12:38).

Mid-opt restart cancels the scan and can leave session WFO candidate
windows on the live book (Friday truncation 06.09). Wait for idle.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig, SystemConfig
from micofx.web.app import create_app

HEAD = {"Origin": "http://testserver"}
APP = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py").read_text(
    encoding="utf-8")


class _Store:
    def __init__(self):
        self.system = SystemConfig()
        self.defaults = {"symbols": [], "group_presets": {}}
        self.symbols = {
            "NAS100": SymbolConfig(symbol="NAS100", magic=1, enabled=True),
        }

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}


class _Client:
    connected = True

    def positions(self):
        return []

    def shutdown(self):
        pass


class _Engine:
    def shutdown(self):
        pass


class _Opt:
    def __init__(self, busy: bool):
        self.busy = busy
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


def test_restart_409_while_optimizer_busy():
    opt = _Opt(True)
    app = create_app(_Store(), _Client(), _Engine(), optimizer=opt)
    tc = TestClient(app)
    res = tc.post("/api/app/restart", headers=HEAD)
    assert res.status_code == 409, res.text
    assert "optimizasyon" in res.json()["detail"].lower()
    assert opt.cancelled is False
    assert getattr(app.state, "_restarting", False) is False


def test_app_restart_checks_busy_before_latch():
    body = APP[APP.index("def app_restart"):APP.index("return app")]
    assert "optimizer.busy" in body
    assert body.index("optimizer.busy") < body.index("_restarting = True")
    assert body.index("optimizer.busy") < body.index("optimizer.cancel()")
