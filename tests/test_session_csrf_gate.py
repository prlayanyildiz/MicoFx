"""Panel POSTs were open on localhost: no token middleware when
MICO_API_TOKEN was empty, and CORS does not stop a foreign page from
POSTing. Found 15.08: Codex + Claude, live
POST /api/bot/panic Origin:https://kotu-site.example -> 200, bot stopped.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

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

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None

    def terminal_flags(self):
        return {}

    def reconnect(self):
        return True

    def set_terminal_path(self, p):
        pass

    def shutdown(self):
        pass


class _Engine:
    def __init__(self):
        self.entry_lock = threading.Lock()
        self.states = {}
        self._sec_cfgs = {}
        self.risk = type("R", (), {"daily": type("D", (), {"resume": lambda self: None})()})()

    def start(self):
        return {"ok": True}

    def stop(self, close_positions=None):
        return {"ok": True}

    def panic(self):
        return {"ok": True}

    def close_all(self, symbol=None):
        return 0, 0

    def shutdown(self):
        pass


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25


# shutdown/restart are on the same gate but must not be POSTed with a
# valid token in fail-first: the old handler would kill the process.
CRITICAL = (
    ("/api/bot/panic", {}),
    ("/api/bot/start", {}),
    ("/api/bot/stop", {}),
    ("/api/app/shutdown", {}),
    ("/api/app/restart", {}),
    ("/api/positions-close-all", {}),
)
LIVE_CRITICAL = (
    ("/api/bot/panic", {}),
    ("/api/bot/start", {}),
    ("/api/bot/stop", {}),
    ("/api/positions-close-all", {}),
)


def _app():
    return create_app(_Store(), _Client(), _Engine(), _Optimizer(), api_token="secret123")


@pytest.mark.parametrize("path,body", CRITICAL)
def test_critical_post_without_secret_is_401(path, body):
    tc = TestClient(_app(), unauth=True)
    res = tc.post(path, json=body)
    assert res.status_code == 401, (path, res.status_code, res.text)


def test_shutdown_and_restart_are_on_the_origin_list():
    from micofx.web import app as web_app
    assert "/api/app/shutdown" in web_app._CRITICAL_MUTATIONS
    assert "/api/app/restart" in web_app._CRITICAL_MUTATIONS


@pytest.mark.parametrize("path,body", LIVE_CRITICAL)
def test_critical_post_from_foreign_origin_is_403(path, body):
    tc = TestClient(_app(), unauth=True)
    res = tc.post(
        path, json=body,
        headers={"X-Mico-Token": "secret123",
                 "Origin": "https://kotu-site.example",
                 "Sec-Fetch-Site": "cross-site"},
    )
    assert res.status_code == 403, (path, res.status_code, res.text)


@pytest.mark.parametrize("path,body", LIVE_CRITICAL)
def test_critical_post_with_missing_origin_is_403(path, body):
    tc = TestClient(_app(), unauth=True)
    res = tc.post(path, json=body, headers={"X-Mico-Token": "secret123"})
    assert res.status_code == 403, (path, res.status_code, res.text)


def test_query_param_token_is_not_accepted_on_panic():
    tc = TestClient(_app(), unauth=True)
    res = tc.post("/api/bot/panic?token=secret123",
                  headers={"Origin": "http://testserver"})
    assert res.status_code == 401


def test_index_sets_httponly_cookie_and_does_not_embed_the_secret():
    tc = TestClient(_app(), unauth=True)
    res = tc.get("/")
    assert res.status_code == 200
    assert "secret123" not in res.text
    cookie = res.cookies.get("mico_session")
    assert cookie == "secret123"
    # Set-Cookie flags: HttpOnly + SameSite=Strict (not in URL).
    raw = res.headers.get("set-cookie", "")
    assert "httponly" in raw.lower()
    assert "samesite=strict" in raw.lower()


def test_same_origin_panic_with_cookie_is_allowed():
    tc = TestClient(_app(), unauth=True)
    tc.get("/")
    res = tc.post("/api/bot/panic",
                  headers={"Origin": "http://testserver"})
    assert res.status_code == 200, res.text
