"""A dead terminal must be launched mid-cycle when autostart_mt5 is on.

Boot-only Popen left the 22.08 hole: MT5 restarted itself, the bot stayed
up, ensure() only called initialize() and never opened terminal64.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.mt5client import MT5Client


def _client(*, autostart: bool) -> tuple[MT5Client, list]:
    launched: list[bool] = []
    c = MT5Client(r"C:\Program Files\MetaTrader 5\terminal64.exe")
    c.autostart = autostart
    c.connected = False
    c._last_attempt = 0.0
    c.ensure_terminal_process = lambda: launched.append(True) or True
    c.connect = lambda: True
    return c, launched


def test_ensure_launches_the_terminal_when_autostart_is_on():
    c, launched = _client(autostart=True)
    assert c.ensure() is True
    assert launched == [True]


def test_ensure_does_not_launch_when_autostart_is_off():
    c, launched = _client(autostart=False)
    assert c.ensure() is True
    assert launched == []
