"""A long copy_rates must release the MT5 lock between chunks.

Optimizer fetches 8000 bars on the live client. One 8000-bar copy_rates
held the lock for the whole IPC; the engine could not trail meanwhile.
"""
from __future__ import annotations

import threading

import numpy as np

from micofx.mt5client import MT5Client


def _rates(n: int, t0: int = 1_000_000):
    dtype = np.dtype([
        ("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"),
        ("close", "f8"), ("tick_volume", "i8"), ("spread", "i4"),
        ("real_volume", "i8"),
    ])
    rows = np.zeros(n, dtype=dtype)
    rows["time"] = np.arange(t0, t0 + n)
    rows["open"] = rows["high"] = rows["low"] = rows["close"] = 100.0
    rows["spread"] = 10
    return rows


def test_a_large_fetch_releases_the_lock_between_chunks(monkeypatch):
    holds: list[int] = []
    lock = threading.RLock()

    def _copy(real, tf, start, count):
        holds.append(count)
        return _rates(int(count), t0=1_000_000 + int(start))

    class _MT5:
        TIMEFRAME_M5 = 5
        TIMEFRAME_M15 = 15
        TIMEFRAME_M30 = 16385
        copy_rates_from_pos = staticmethod(_copy)

    monkeypatch.setattr("micofx.mt5client.mt5", _MT5)
    client = object.__new__(MT5Client)
    client._lock = lock
    client.select = lambda symbol: symbol
    client.connected = True

    bars = MT5Client.bars(client, "GER40", "M5", 5000)
    assert bars is not None
    assert len(holds) >= 2
    assert max(holds) <= 2500
    assert len(bars) == 5000
