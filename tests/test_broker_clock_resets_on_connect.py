"""Broker clock bookkeeping must restart on every MT5 attach."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.mt5client import MT5Client


def _client() -> MT5Client:
    c = object.__new__(MT5Client)
    c._broker_now = 1000.0
    c._broker_seen_at = time.time()
    c._broker_anchor = (time.time() - 3600, 900.0)
    c._info_cache = {}
    c._tick_cache = {}
    c._margin_cache = {}
    c._name_map = {}
    c._symbol_names_cache = []
    c._symbol_names_at = 0.0
    c.connected = True
    c.last_error = ""
    c._ipc_failed_start_key = ""
    return c


def test_after_connect_clears_broker_clock_state(monkeypatch):
    c = _client()
    monkeypatch.setattr(
        "micofx.mt5client.mt5.terminal_info",
        lambda: type("T", (), {"trade_allowed": True, "company": "X"})())
    monkeypatch.setattr(
        "micofx.mt5client.mt5.account_info",
        lambda: type("A", (), {"login": 1, "server": "S"})())
    assert c._after_connect() is True
    assert c._broker_now == 0.0
    assert c._broker_seen_at == 0.0
    assert c._broker_last_advance_at == 0.0
    assert c._broker_anchor is None


def test_time_msc_advances_the_broker_clock(monkeypatch):
    """When the second field stalls, sub-second progress still counts."""
    c = object.__new__(MT5Client)
    c._broker_now = 0.0
    c._broker_seen_at = 0.0
    c._broker_anchor = None
    c._tick_cache = {}
    c._lock = type("L", (), {"__enter__": lambda s: None, "__exit__": lambda s, *a: None})()

    class _Tick:
        bid = 1.0
        ask = 1.1
        time = 1000
        time_msc = 1000_500  # +0.5s vs naive second field

    monkeypatch.setattr("micofx.mt5client.mt5.symbol_info_tick", lambda _real: _Tick())
    monkeypatch.setattr(MT5Client, "select", lambda self, sym: "GER40")

    tick = MT5Client.tick(c, "GER40")
    assert tick is not None
    assert tick["time"] == 1000.5
    assert c._broker_now == 1000.5
