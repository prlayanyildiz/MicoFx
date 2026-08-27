"""Deposits rarely move. history_deals_get every ~2s cycle is wasted lock.

Claude 27.08: cash_flow_since scans the same day window as day_stats, but
the call has no TTL. Demo deposits change once in a blue moon. Skip the
IPC when balance is unchanged and the last good fetch is fresh. A balance
jump (the 13.08 +500 case) must still fetch immediately.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


def _eng(balance=1000.0):
    fetches = []

    class _Daily:
        def set_cash_flow(self, value):
            self.last = value

    client = SimpleNamespace(
        cash_flow_since=lambda ts: fetches.append(ts) or 0.0,
    )
    eng = Engine.__new__(Engine)
    eng.client = client
    eng.risk = SimpleNamespace(daily=_Daily())
    eng._account = {"balance": balance}
    eng._day_start_epoch = lambda: 1.0
    return eng, fetches


def test_a_second_cycle_with_the_same_balance_does_not_hit_history():
    eng, fetches = _eng()
    Engine._refresh_cash_flow(eng)
    Engine._refresh_cash_flow(eng)
    assert fetches == [1.0]


def test_a_deposit_shaped_balance_jump_fetches_immediately():
    eng, fetches = _eng(1000.0)
    Engine._refresh_cash_flow(eng)
    eng._account = {"balance": 1500.0}
    Engine._refresh_cash_flow(eng)
    assert len(fetches) == 2


def test_a_failed_history_call_does_not_start_the_ttl():
    """None must not stamp 'fresh' — the next cycle has to retry."""
    fetches = []

    class _Daily:
        def set_cash_flow(self, value):
            self.last = value

    n = {"i": 0}

    def _since(ts):
        fetches.append(ts)
        n["i"] += 1
        return None if n["i"] == 1 else 0.0

    eng = Engine.__new__(Engine)
    eng.client = SimpleNamespace(cash_flow_since=_since)
    eng.risk = SimpleNamespace(daily=_Daily())
    eng._account = {"balance": 1000.0}
    eng._day_start_epoch = lambda: 1.0
    Engine._refresh_cash_flow(eng)
    Engine._refresh_cash_flow(eng)
    assert len(fetches) == 2
    assert eng.risk.daily.last == 0.0
