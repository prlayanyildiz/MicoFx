"""``mt5_terminal_path`` was a panel-writable string that becomes a Popen.

The stored value goes to ``MT5Client._exe_from_path``, which appends
``terminal64.exe`` when handed a directory and otherwise takes the path as
given, and ``ensure_terminal_process`` then runs it:

    subprocess.Popen([str(exe)], cwd=str(exe.parent), ...)

``autostart_mt5`` ships True, so an accepted POST is a launched process. The
handler stored the field with no validation of any kind - while ``backup_dir``
one screen above gets an absolute-path check, a drive-root check and a UNC
latch. The two fields have the same threat shape and only one was guarded.

The rules mirror ``backup_dir``: absolute local path or UNC, no drive root,
and - the part specific to this field - if a file is named it must be
``terminal64.exe``. A directory stays legal because that is what the live book
carries (``C:\\Program Files\\MetaTrader 5``) and ``_exe_from_path`` resolves it.
Emptying the field stays legal; empty means "refuse auto-attach".
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
    mt5_terminal_path = r"C:\Program Files\MetaTrader 5"
    autostart_mt5 = True
    backup_dir_allow_unc = False
    backup_keep = 7

    def to_dict(self):
        return {"mt5_terminal_path": self.mt5_terminal_path}


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

    def update_system(self, patch, source=""):
        for k, v in patch.items():
            setattr(self.system, k, v)
        return self.system


class _Client:
    connected = True
    last_error = ""
    autostart = True

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None

    def terminal_flags(self):
        return {}

    def set_terminal_path(self, p):
        self.path = p

    def reconnect(self):
        return True


class _Engine:
    def __init__(self):
        self.entry_lock = threading.Lock()
        self.states = {}
        self._sec_cfgs = {}


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25

    def start(self, *a, **k):
        return {"ok": True}


def _post(path):
    store = _Store()
    tc = TestClient(create_app(store, _Client(), _Engine(), _Optimizer()))
    return tc.post("/api/system", json={"mt5_terminal_path": path},
                   headers=HEAD), store


# ------------------------------------------------------------- the defect

@pytest.mark.parametrize("path", [
    r"C:\Windows\System32\calc.exe",
    r"C:\Users\Administrator\payload.exe",
    r"C:\Program Files\MetaTrader 5\metaeditor64.exe",
])
def test_an_executable_that_is_not_the_terminal_is_refused(path):
    res, store = _post(path)
    assert res.status_code == 400, res.text
    assert store.system.mt5_terminal_path == r"C:\Program Files\MetaTrader 5"


@pytest.mark.parametrize("path", ["terminal64.exe", "notapath", r"..\..\x"])
def test_a_relative_path_is_refused(path):
    assert _post(path)[0].status_code == 400


def test_a_drive_root_is_refused():
    assert _post("C:\\")[0].status_code == 400


def test_a_unc_path_is_refused_while_the_latch_is_off():
    assert _post(r"\\nas\mt5\terminal64.exe")[0].status_code == 400


# --------------------------------------------------- what must keep working

def test_the_directory_the_live_book_carries_is_accepted():
    res, store = _post(r"C:\Program Files\MetaTrader 5")
    assert res.status_code == 200, res.text
    assert store.system.mt5_terminal_path == r"C:\Program Files\MetaTrader 5"


def test_naming_terminal64_directly_is_accepted():
    res, _ = _post(r"C:\Program Files\MetaTrader 5\terminal64.exe")
    assert res.status_code == 200, res.text


def test_clearing_the_field_is_accepted():
    """Empty means refuse auto-attach, which is a legitimate setting."""
    res, store = _post("")
    assert res.status_code == 200, res.text
    assert store.system.mt5_terminal_path == ""


def test_the_case_of_the_exe_name_does_not_matter():
    res, _ = _post(r"C:\Program Files\MetaTrader 5\TERMINAL64.EXE")
    assert res.status_code == 200, res.text
