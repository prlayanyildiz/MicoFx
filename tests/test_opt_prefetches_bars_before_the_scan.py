"""Opt must download every symbol's bars before any sweep starts.

Overlapping copy_rates with the pool kept the MT5 lock dripping for the
whole first-symbol wall clock so the next window could start. Combo eval
is the hours; the lock drip is what the live cycle feels. Prefetch, then
scan.
"""
from __future__ import annotations

import sys
import threading
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


class _Done(Future):
    def __init__(self, job):
        super().__init__()
        self.set_result({
            "ok": False, "error": "test",
            "timeframe": job.get("timeframe"),
            "strategy": job.get("strategy"),
            "order": job.get("order", 0),
        })


class _Pool:
    def __init__(self, submitted, *a, **k):
        self.submitted = submitted

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def submit(self, fn, job):
        self.submitted.append(job["symbol"])
        return _Done(job)

    def shutdown(self, wait=True, cancel_futures=False):
        return None


def test_every_symbol_is_fetched_before_any_sweep_is_submitted():
    fetches: list[str] = []
    submitted: list[str] = []
    opt = Optimizer.__new__(Optimizer)
    opt._cancel = threading.Event()
    opt._lock = threading.RLock()
    opt.job = {"state": "running"}
    opt._set = lambda **k: None

    def plan_next(symbol):
        assert submitted == [], (
            f"sweep {submitted} started before {symbol} bars were fetched")
        fetches.append(symbol)
        return [{"symbol": symbol, "timeframe": "M30",
                 "strategy": "burst", "order": 0}]

    def note(job, outcome):
        return None

    with patch("micofx.optimizer.ProcessPoolExecutor",
               lambda **k: _Pool(submitted)):
        opt._search_parallel(["GER40", "US30", "XAUUSD"], plan_next, note, 2)
    assert fetches == ["GER40", "US30", "XAUUSD"]
    assert submitted == ["GER40", "US30", "XAUUSD"]
