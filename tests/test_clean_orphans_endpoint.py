"""The panel's orphan-sweep button, and the one thing it must not do.

``POST /api/system/clean-orphans`` force-kills processes. The first version
called ``gece_restart.cleanup_orphan_workers`` and then ran a *second*
PowerShell of its own that selected on process name plus
``--multiprocessing-fork`` and nothing else - no venv image, no dead-parent
check. That is the exact filter
``tests/test_orphan_sweep_stays_in_its_own_venv.py`` was written to forbid:
it reaches every Python multiprocessing worker on the machine, and a click
during a search would have killed this process's own pool.

The endpoint owns no filter now, so these tests guard the delegation rather
than the query, and nothing here is allowed to reach a real Stop-Process -
the earlier version of this file called the endpoint unpatched, so running
the suite while a search was live would have swept the live pool.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gece_restart
from micofx.models import SymbolConfig
from micofx.web import app as web_app
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

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None

    def terminal_flags(self):
        return {}


class _Engine:
    running = True

    def stats(self):
        return {}

    def get_daily_loss_stats(self):
        return {}


class _Optimizer:
    busy = False

    def cancel(self):
        return {"ok": True}


def _app():
    return create_app(_Store(), _Client(), _Engine(), _Optimizer(), api_token="test_secret")


HEADERS = {"X-Mico-Token": "test_secret", "Origin": "http://testserver"}


def _no_real_kill(monkeypatch, killed: int = 0) -> list:
    """Stand in for the sweep. A test that force-kills is not a test."""
    seen: list = []

    def _fake(executable=None):
        seen.append(executable)
        return killed

    monkeypatch.setattr(gece_restart, "cleanup_orphan_workers", _fake)
    return seen


def test_clean_orphans_requires_auth(monkeypatch):
    _no_real_kill(monkeypatch)
    tc = TestClient(_app(), unauth=True)
    res = tc.post("/api/system/clean-orphans", json={})
    assert res.status_code == 401


def test_clean_orphans_reports_what_the_sweep_killed(monkeypatch):
    seen = _no_real_kill(monkeypatch, killed=3)
    tc = TestClient(_app(), unauth=True)
    res = tc.post("/api/system/clean-orphans", json={}, headers=HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["killed"] == 3
    assert "3" in data["message"]
    assert seen == [sys.executable], "supurge bu yorumlayiciya baglanmadi"


def test_a_clean_machine_says_so(monkeypatch):
    _no_real_kill(monkeypatch, killed=0)
    tc = TestClient(_app(), unauth=True)
    data = tc.post("/api/system/clean-orphans", json={}, headers=HEADERS).json()
    assert data["killed"] == 0
    assert "bulunamadi" in data["message"]


def test_a_sweep_failure_does_not_500_the_panel(monkeypatch):
    def _boom(executable=None):
        raise OSError("powershell yok")

    monkeypatch.setattr(gece_restart, "cleanup_orphan_workers", _boom)
    tc = TestClient(_app(), unauth=True)
    res = tc.post("/api/system/clean-orphans", json={}, headers=HEADERS)
    assert res.status_code == 200
    assert res.json()["killed"] == 0


def test_the_endpoint_does_not_carry_a_second_filter():
    """The guarded filter is the only filter. A copy here would not be seen
    by test_orphan_sweep_stays_in_its_own_venv, which is how the unscoped one
    got in."""
    src = Path(web_app.__file__).read_text(encoding="utf-8")
    body = src.split('@app.post("/api/system/clean-orphans")', 1)[1]
    body = body.split("return app", 1)[0]
    # Past the docstring: the prose there names the filter it must not carry.
    code = body.split('"""', 2)[-1]
    assert "cleanup_orphan_workers" in code
    assert "--multiprocessing-fork" not in code
    assert "Get-CimInstance" not in code
    assert "Stop-Process" not in code
    assert "subprocess" not in code
