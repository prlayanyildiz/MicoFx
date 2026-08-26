"""/api/state must not call order_calc_margin per symbol every 3s.

capacity() walks every symbol through margin_for (MT5 lock). The cycle
book already reused positions/account; capacity was the leftover N+1.
"""
from __future__ import annotations

import time
from types import SimpleNamespace

from micofx.engine import Engine
from micofx.models import SymbolConfig


def _eng() -> Engine:
    eng = object.__new__(Engine)
    eng.client = SimpleNamespace(connected=True)
    eng.store = SimpleNamespace(
        symbols={"GER40": SymbolConfig(symbol="GER40", magic=1)},
        system=SimpleNamespace(poll_interval_sec=2.0),
    )
    eng._positions = []
    eng.last_cycle_at = time.time()
    eng._capacity_cache = {}
    eng._capacity_cache_at = 0.0
    eng._capacity_pos_sig = ()
    eng.risk = SimpleNamespace(capacity_calls=0)

    def _cap(positions, account, atrs):
        eng.risk.capacity_calls += 1
        return {"rows": [], "open_total": len(positions)}

    eng.risk.capacity = _cap
    return eng


def test_a_quiet_book_reuses_capacity_within_ttl():
    eng = _eng()
    pos = [{"ticket": 1, "volume": 0.1, "magic": 1}]
    acc = {"equity": 1000.0}
    atrs = {"GER40": 10.0}
    a = Engine._panel_capacity(eng, pos, acc, atrs)
    b = Engine._panel_capacity(eng, pos, acc, atrs)
    assert a == b
    assert eng.risk.capacity_calls == 1


def test_a_new_ticket_invalidates_capacity():
    eng = _eng()
    acc = {"equity": 1000.0}
    atrs = {"GER40": 10.0}
    Engine._panel_capacity(eng, [{"ticket": 1, "volume": 0.1}], acc, atrs)
    Engine._panel_capacity(eng, [{"ticket": 2, "volume": 0.1}], acc, atrs)
    assert eng.risk.capacity_calls == 2
