"""opt_runs must say how an apply landed, not let us infer it from the clock.

The 11-16.08 book had 46 applies after the 48h settling brake, 40 of them
younger than 48 hours. Those were force. The payload had no ``force`` key,
so the count was a gap inference. Same write should also keep the apply
instant (a search can sit hours before it is applied) and the strategy/
timeframe it replaced. Old rows stay key-less: ``None`` is not ``False``.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_closed_symbol_scan_does_not_apply import _finish_opt, _finish_plan


def test_an_applied_run_records_force_time_and_previous():
    opt, store = _finish_opt()
    plan, _ = _finish_plan(enabled=True)
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    before = time.time()
    opt._finish_symbol(plan, apply_best=True)
    payload = store.runs[-1]["payload"]
    assert payload["force"] is True
    assert payload["applied_at"] is not None
    assert payload["applied_at"] >= before
    assert payload["previous"] == {"strategy": "t3_stoch", "timeframe": "M5"}


def test_a_run_that_does_not_apply_does_not_pretend_it_did():
    opt, store = _finish_opt()
    plan, _ = _finish_plan(enabled=False)
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    opt._finish_symbol(plan, apply_best=True)
    payload = store.runs[-1]["payload"]
    assert payload["force"] is True
    assert payload["applied_at"] is None
    assert payload["previous"] is None


def test_force_false_is_not_the_same_as_a_missing_key():
    """Old rows have no key. New unforced rows must store False, not omit."""
    opt, store = _finish_opt()
    opt._force_apply = False
    plan, _ = _finish_plan(enabled=True)
    # Age guard: incumbent epoch is 1.0, decades old, so apply is allowed.
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    opt._finish_symbol(plan, apply_best=True)
    payload = store.runs[-1]["payload"]
    assert "force" in payload
    assert payload["force"] is False
    assert store.runs[-1]["applied"] is True
    assert payload["previous"]["strategy"] == "t3_stoch"
