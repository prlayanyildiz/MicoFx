"""Panel snapshot must not take history_deals_get on the web thread.

Halt / cycle still fetch (5s). snapshot serves the last cache, even if stale.
"""
from __future__ import annotations

import inspect
import time
from types import SimpleNamespace

from micofx.engine import Engine


def test_snapshot_does_not_fetch_day_stats():
    src = inspect.getsource(Engine.snapshot)
    assert "fetch=False" in src


def test_the_cycle_warms_day_stats():
    src = inspect.getsource(Engine._cycle)
    assert "self.day_stats(" in src


def test_symbol_halt_still_uses_the_short_day_cache():
    src = inspect.getsource(Engine._symbol_daily_halt)
    assert "self.day_stats()" in src
    assert "max_age" not in src.split("self.day_stats()", 1)[1][:80]


def test_day_stats_serves_a_stale_cache_when_fetch_is_off():
    eng = object.__new__(Engine)
    eng._day_cache = {"realised": 42.0}
    eng._day_cache_at = time.time() - 60.0
    eng.risk = SimpleNamespace(daily=SimpleNamespace(day_key="x"))
    eng.client = SimpleNamespace(
        deals_since=lambda ts: (_ for _ in ()).throw(
            AssertionError("deals_since on a fetch=False snapshot")),
        merge_round_trips=lambda deals: deals,
    )
    assert Engine.day_stats(eng, max_age=15.0, fetch=False)["realised"] == 42.0
