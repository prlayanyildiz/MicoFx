"""Boot used to wait on mt5.initialize() before uvicorn bound.

02.09 PC restart: start_silent.vbs opened the browser at 2.5s, run.py was
still inside a 60s IPC timeout, GET / never answered, and every later
/api/state queued on the same lock. The watch loop still attaches; the
HTTP server must not wait for it.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run as run_module
from micofx.mt5client import MT5Client


def test_main_does_not_call_connect_before_bind():
    src = inspect.getsource(run_module.main)
    assert "uvicorn.run" in src
    assert "ensure_terminal_process" in src
    # Attach is the cycle's job. A wait loop of connect() before bind is
    # the reboot hang: each initialize() is the IPC timeout, and the
    # browser is already open.
    assert "client.connect()" not in src
    assert "autostart_mt5_wait_sec" not in src
    assert "start_watch" in src
    assert "add_event_handler" in src or "on_event" in src


def test_initialize_uses_a_short_ipc_timeout():
    """Default MetaTrader5 timeout is 60s. That froze the GIL and the panel."""
    from micofx import mt5client as mod

    assert mod._INITIALIZE_TIMEOUT_MS <= 10_000
    src = inspect.getsource(MT5Client.connect)
    assert "timeout=" in src
    assert "_INITIALIZE_TIMEOUT_MS" in src
    # The package ignores timeout= (probe: 2000ms still waited 60s). The
    # real panel-safe gate is skipping initialize until the log is synced.
    assert "_ipc_ready" in src


def test_autostart_bot_retries_after_bind_instead_of_one_shot():
    """Timer(3s, start) fired while IPC was still down; trading never opened."""
    src = inspect.getsource(run_module.main)
    assert "autostart_bot" in src
    assert "Timer(3.0, engine.start)" not in src
    assert "_retry_autostart" in src
    assert "allow_initialize" in src
