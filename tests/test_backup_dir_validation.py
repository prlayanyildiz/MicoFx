"""POST /api/system - backup_dir validation (B3).

A UNC backup_dir sends the whole project (code + settings DB) over the
network to whatever share is named - previously accepted unconditionally.
Now requires Store `backup_dir_allow_unc` already true. Same-request HTTP
latch is 400. Local drive-letter paths are unaffected.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SystemConfig
from micofx.web.app import create_app


class _FakeStore:
    def __init__(self):
        self.system = SystemConfig()
        self.symbols: dict = {}
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def update_system(self, patch, source=""):
        current = self.system.to_dict()
        for key, value in patch.items():
            if value is not None:
                current[key] = value
        self.system = SystemConfig.from_dict(current)
        return self.system


class _FakeClient:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return None


class _FakeEngine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


def _client():
    store = _FakeStore()
    app = create_app(store, _FakeClient(), _FakeEngine(), optimizer=None)
    return TestClient(app), store


def test_backup_dir_unc_rejected_without_store_opt_in():
    tc, store = _client()
    res = tc.post("/api/system", json={"backup_dir": r"\\nas\share\backups"})
    assert res.status_code == 400
    assert store.system.backup_dir != r"\\nas\share\backups"


def test_backup_dir_unc_opt_in_is_not_an_http_key():
    """Same-request latch left with the panel. Store flag still opens UNC."""
    tc, store = _client()
    res = tc.post("/api/system", json={
        "backup_dir": r"\\nas\share\backups", "backup_dir_allow_unc": True,
    })
    assert res.status_code == 400
    assert store.system.backup_dir != r"\\nas\share\backups"
    assert store.system.backup_dir_allow_unc is False


def test_backup_dir_unc_accepted_when_already_opted_in():
    tc, store = _client()
    store.system = SystemConfig.from_dict({**store.system.to_dict(), "backup_dir_allow_unc": True})
    res = tc.post("/api/system", json={"backup_dir": r"\\nas\share\backups"})
    assert res.status_code == 200


def test_backup_dir_local_path_unaffected_by_unc_gate():
    tc, store = _client()
    res = tc.post("/api/system", json={"backup_dir": r"D:\MicoFX_Yedek"})
    assert res.status_code == 200
    assert store.system.backup_dir == r"D:\MicoFX_Yedek"


def test_backup_dir_bare_drive_root_still_rejected():
    tc, store = _client()
    res = tc.post("/api/system", json={"backup_dir": "C:\\"})
    assert res.status_code == 400
