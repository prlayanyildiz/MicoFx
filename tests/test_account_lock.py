"""Account lock: refuse entries when the terminal is on a different login.

Found 16.08: the operator logged the terminal into Pepperstone live
51501624 while MicoFX was running against demo 61562752. MT5Client uses
whichever account is open; there was no login/server check. Balance was
$0.51 so no order filled — luck, not a gate.

These tests pin the three behaviours the brief asked for: mismatch
refuses, matching login+server allows, empty lock binds the first
account (logged by the engine, not silent).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.account_lock import decide_account_lock
from micofx.engine import Engine
from micofx.models import SystemConfig
from micofx.web.app import create_app


def test_lock_refuses_a_different_login():
    """61562752 expected, client returns 51501624 — must not allow entries."""
    d = decide_account_lock(61562752, "Pepperstone-Demo", 51501624, "PepperstoneBS-MT5-Live01")
    assert d.allow_entry is False
    assert "61562752" in d.reason
    assert "51501624" in d.reason
    assert d.bind_login is None


def test_lock_allows_the_same_account():
    d = decide_account_lock(61562752, "Pepperstone-Demo", 61562752, "Pepperstone-Demo")
    assert d.allow_entry is True
    assert d.reason == ""
    assert d.bind_login is None


def test_empty_lock_binds_the_first_account():
    d = decide_account_lock(0, "", 61562752, "Pepperstone-Demo", trade_mode=0)
    assert d.allow_entry is True
    assert d.bind_login == 61562752
    assert d.bind_server == "Pepperstone-Demo"


def test_empty_lock_does_not_bind_a_real_money_account():
    """Live 16.08: empty lock wrote the first connected login; that login
    was trade_mode==2. Auto-bind must refuse and wait for operator confirm."""
    d = decide_account_lock(
        0, "", 51501624, "PepperstoneBS-MT5-Live01", trade_mode=2,
    )
    assert d.allow_entry is False
    assert d.bind_login is None
    assert d.bind_server is None
    assert "operator" in d.reason.lower() or "onay" in d.reason.lower()
    assert "gercek para" in d.reason.lower() or "live" in d.reason.lower()


class _Store:
    def __init__(self, login=61562752, server="Pepperstone-Demo"):
        self.system = SystemConfig(account_lock_login=login, account_lock_server=server)
        self.updates = []

    def update_system(self, patch, source=""):
        self.updates.append((dict(patch), source))
        current = self.system.to_dict()
        current.update(patch)
        self.system = SystemConfig.from_dict(current)
        return self.system


def _engine(store):
    eng = object.__new__(Engine)
    eng.store = store
    eng._account_lock_reason = ""
    return eng


def test_engine_mismatch_sets_reason_and_does_not_rebind():
    store = _Store()
    eng = _engine(store)
    reason = eng._enforce_account_lock({
        "login": 51501624, "server": "PepperstoneBS-MT5-Live01",
    })
    assert "beklenen 61562752" in reason
    assert store.system.account_lock_login == 61562752
    assert store.updates == []


def test_engine_empty_lock_writes_the_connected_account():
    store = _Store(login=0, server="")
    eng = _engine(store)
    reason = eng._enforce_account_lock({
        "login": 61562752, "server": "Pepperstone-Demo", "trade_mode": 0,
    })
    assert reason == ""
    assert store.system.account_lock_login == 61562752
    assert store.system.account_lock_server == "Pepperstone-Demo"
    assert store.updates[0][1] == "hesap-kilidi"


def test_engine_empty_lock_does_not_bind_a_real_money_account():
    store = _Store(login=0, server="")
    eng = _engine(store)
    reason = eng._enforce_account_lock({
        "login": 51501624, "server": "PepperstoneBS-MT5-Live01", "trade_mode": 2,
    })
    assert reason
    assert "onay" in reason.lower() or "operator" in reason.lower()
    assert store.system.account_lock_login == 0
    assert store.updates == []


def test_enforce_passes_trade_mode_into_the_lock():
    src = Path("micofx/engine.py").read_text(encoding="utf-8")
    body = src.split("def _enforce_account_lock(", 1)[1].split("\n    def ", 1)[0]
    assert "trade_mode" in body
    assert "decide_account_lock" in body


def test_empty_lock_copy_does_not_promise_to_bind_live():
    src = Path("micofx/web/static/app.js").read_text(encoding="utf-8")
    assert "ilk bagli hesap yazilir" not in src
    assert "ilk baglanan hesap yazilir" not in src


def test_cycle_allow_entry_is_gated_on_the_lock_reason():
    """Mismatch must reach allow_entry, not only a helper that nothing calls."""
    src = Path("micofx/engine.py").read_text(encoding="utf-8")
    body = src.split("def _cycle(", 1)[1].split("\n    def ", 1)[0]
    assert "lock_reason" in body
    assert "not lock_reason" in body
    # H2: flatten uses broker/server fallback when decision clock is stale.
    assert "self.manage_positions(self._flatten_clock(server_now))" in body
    assert body.index("self.manage_positions(self._flatten_clock(server_now))") < body.index(
        "not lock_reason")


class _WebStore:
    def __init__(self):
        self.system = SystemConfig(account_lock_login=61562752, account_lock_server="Pepperstone-Demo")
        self.symbols = {}
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def update_system(self, patch, source=""):
        current = self.system.to_dict()
        current.update({k: v for k, v in patch.items() if v is not None})
        self.system = SystemConfig.from_dict(current)
        return self.system


class _WebClient:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return None


class _WebEngine:
    def __init__(self, account):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}
        self._account = account
        self._account_lock_reason = ""

    def refresh_account(self, force=False):
        return self._account

    def _enforce_account_lock(self, account):
        self._account_lock_reason = "checked"
        return ""


def _web(account):
    store = _WebStore()
    app = create_app(store, _WebClient(), _WebEngine(account), optimizer=None, api_token="secret123")
    tc = TestClient(app)
    headers = {
        "X-Mico-Token": "secret123",
        "Origin": "http://testserver",
    }
    return tc, store, headers


def test_system_patch_cannot_rewrite_the_lock():
    tc, store, headers = _web({"login": 51501624, "server": "PepperstoneBS-MT5-Live01"})
    res = tc.post(
        "/api/system",
        json={"account_lock_login": 51501624, "account_lock_server": "PepperstoneBS-MT5-Live01"},
        headers=headers,
    )
    assert res.status_code == 400
    assert store.system.account_lock_login == 61562752


def test_account_lock_confirm_refuses_when_typed_login_is_not_connected():
    tc, store, headers = _web({"login": 51501624, "server": "PepperstoneBS-MT5-Live01"})
    res = tc.post(
        "/api/account-lock",
        json={"confirm_login": 61562752, "confirm_server": "Pepperstone-Demo"},
        headers=headers,
    )
    assert res.status_code == 400
    assert store.system.account_lock_login == 61562752


def test_account_lock_confirm_rewrites_only_when_operator_matches_connected():
    tc, store, headers = _web({"login": 51501624, "server": "PepperstoneBS-MT5-Live01"})
    res = tc.post(
        "/api/account-lock",
        json={"confirm_login": 51501624, "confirm_server": "PepperstoneBS-MT5-Live01"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert store.system.account_lock_login == 51501624
    assert store.system.account_lock_server == "PepperstoneBS-MT5-Live01"
