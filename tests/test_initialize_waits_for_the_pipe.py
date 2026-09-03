"""mt5.initialize() holds the GIL until the IPC timeout.

02.09 reboot: the terminal log was still on 'started' and every connect()
froze the interpreter for 60s. A background thread does not help — the C
extension never releases the GIL. Skip initialize until the same log says
terminal synchronized; the watch loop sleeps between tries.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.mt5client import MT5Client


def _install(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    exe = tmp_path / "install" / "terminal64.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"mz")
    roaming = tmp_path / "Roaming"
    data = roaming / "MetaQuotes" / "Terminal" / "HASH1"
    (data / "logs").mkdir(parents=True)
    (data / "origin.txt").write_text(str(exe.parent.resolve()), encoding="utf-16")
    monkeypatch.setenv("APPDATA", str(roaming))
    return exe, data / "logs" / time.strftime("%Y%m%d.log")


def test_ipc_ready_is_false_until_the_log_says_synchronized(tmp_path, monkeypatch):
    exe, log = _install(tmp_path, monkeypatch)
    client = MT5Client(str(exe))
    log.write_text(
        "GQ\t0\t00:00:01.000\tTerminal\tMetaTrader 5 x64 build 1 started for MetaQuotes Ltd.\n",
        encoding="utf-8",
    )
    assert client._ipc_ready(exe) is False
    log.write_text(
        "GQ\t0\t00:00:01.000\tTerminal\tMetaTrader 5 x64 build 1 started for MetaQuotes Ltd.\n"
        "HI\t0\t00:00:05.000\tNetwork\t'1': terminal synchronized with Broker: 0 positions\n",
        encoding="utf-8",
    )
    assert client._ipc_ready(exe) is True


def test_a_fresh_start_line_without_sync_is_not_ready(tmp_path, monkeypatch):
    """Yesterday's sync must not authorize today's unfinished boot."""
    exe, log = _install(tmp_path, monkeypatch)
    client = MT5Client(str(exe))
    log.write_text(
        "HI\t0\t00:00:05.000\tNetwork\t'1': terminal synchronized with Broker\n"
        "GQ\t0\t00:10:00.000\tTerminal\tMetaTrader 5 x64 build 1 started for MetaQuotes Ltd.\n",
        encoding="utf-8",
    )
    assert client._ipc_ready(exe) is False


def test_missing_today_log_falls_back_to_yesterdays_sync(tmp_path, monkeypatch):
    """03.09 gece restart: calendar rolled, terminal still on yesterday's file."""
    exe, today_log = _install(tmp_path, monkeypatch)
    logs = today_log.parent
    yesterday = (time.time() - 86400)
    prior = logs / time.strftime("%Y%m%d.log", time.localtime(yesterday))
    if prior == today_log:
        prior = logs / "19990101.log"
    prior.write_text(
        "GQ\t0\t01:17:51.000\tTerminal\tMetaTrader 5 x64 build 1 started for MetaQuotes Ltd.\n"
        "HI\t0\t01:17:54.000\tNetwork\t'1': terminal synchronized with Broker\n",
        encoding="utf-8",
    )
    if today_log.is_file():
        today_log.unlink()
    client = MT5Client(str(exe))
    assert client._ipc_ready(exe) is True
    assert client._boot_key(exe)


def test_connect_does_not_call_initialize_before_ipc_ready(tmp_path, monkeypatch):
    exe, log = _install(tmp_path, monkeypatch)
    log.write_text(
        "GQ\t0\t00:00:01.000\tTerminal\tMetaTrader 5 x64 build 1 started for MetaQuotes Ltd.\n",
        encoding="utf-8",
    )
    calls = {"n": 0}

    fake = SimpleNamespace(
        initialize=lambda **_k: calls.__setitem__("n", calls["n"] + 1) or True,
        last_error=lambda: (-10003, "Pipe server didn't answer in 60 sec"),
        shutdown=lambda: None,
        terminal_info=lambda: None,
        account_info=lambda: None,
    )
    monkeypatch.setattr("micofx.mt5client.mt5", fake)
    client = MT5Client(str(exe))
    assert client.connect() is False
    assert calls["n"] == 0
    assert "hazir" in client.last_error.lower() or "IPC" in client.last_error


def _synced_log(log: Path) -> None:
    log.write_text(
        "GQ\t0\t00:00:01.000\tTerminal\tMetaTrader 5 x64 build 1 started for MetaQuotes Ltd.\n"
        "HI\t0\t00:00:05.000\tNetwork\t'1': terminal synchronized with Broker: 0 positions\n",
        encoding="utf-8",
    )


def test_connect_does_not_call_initialize_until_armed(tmp_path, monkeypatch):
    exe, log = _install(tmp_path, monkeypatch)
    _synced_log(log)
    calls = {"n": 0}
    fake = SimpleNamespace(
        initialize=lambda **_k: calls.__setitem__("n", calls["n"] + 1) or True,
        last_error=lambda: (1, "ok"),
        shutdown=lambda: None,
        terminal_info=lambda: None,
        account_info=lambda: None,
    )
    monkeypatch.setattr("micofx.mt5client.mt5", fake)
    client = MT5Client(str(exe))
    client.allow_initialize = False
    assert client.connect() is False
    assert calls["n"] == 0


def test_a_failed_initialize_is_not_retried_on_the_same_boot(tmp_path, monkeypatch):
    """02.09: every 5s reconnect re-entered the 60s GIL wait after -10003."""
    exe, log = _install(tmp_path, monkeypatch)
    _synced_log(log)
    calls = {"n": 0}
    fake = SimpleNamespace(
        initialize=lambda **_k: calls.__setitem__("n", calls["n"] + 1) or False,
        last_error=lambda: (-10003, "Pipe server didn't answer in 60 sec"),
        shutdown=lambda: None,
        terminal_info=lambda: None,
        account_info=lambda: None,
    )
    monkeypatch.setattr("micofx.mt5client.mt5", fake)
    client = MT5Client(str(exe))
    client._last_attempt = 0.0
    assert client.connect() is False
    assert calls["n"] == 1
    assert client.connect() is False
    assert calls["n"] == 1
    client.clear_ipc_latch()
    assert client.connect() is False
    assert calls["n"] == 2


def test_reconnect_clears_the_ipc_latch(tmp_path, monkeypatch):
    exe, log = _install(tmp_path, monkeypatch)
    _synced_log(log)
    calls = {"n": 0}
    fake = SimpleNamespace(
        initialize=lambda **_k: calls.__setitem__("n", calls["n"] + 1) or False,
        last_error=lambda: (-10003, "Pipe server didn't answer in 60 sec"),
        shutdown=lambda: None,
        terminal_info=lambda: None,
        account_info=lambda: None,
    )
    monkeypatch.setattr("micofx.mt5client.mt5", fake)
    client = MT5Client(str(exe))
    client._last_attempt = 0.0
    assert client.connect() is False
    assert client._ipc_latched(exe)
    client.reconnect()
    assert calls["n"] == 2
