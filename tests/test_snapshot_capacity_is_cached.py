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
        system=SimpleNamespace(
            poll_interval_sec=2.0,
            lot_multiplier=1.0,
            max_margin_usage_pct=50.0,
            max_concurrent_risk_pct=8.0,
            size_by_edge=False,
        ),
    )
    eng._positions = []
    eng.last_cycle_at = time.time()
    eng._capacity_cache = {}
    eng._capacity_cache_at = 0.0
    eng._capacity_pos_sig = ()
    eng._capacity_sys_sig = ()
    eng.risk = SimpleNamespace(capacity_calls=0)

    def _cap(positions, account, atrs, autopsies=None):
        eng.risk.capacity_calls += 1
        return {"rows": [], "open_total": len(positions)}

    eng.risk.capacity = _cap
    eng.risk.fill_holdout_projection = lambda rows, balance: {}
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


def test_a_sizing_change_invalidates_capacity():
    eng = _eng()
    acc = {"equity": 1000.0}
    atrs = {"GER40": 10.0}
    pos = [{"ticket": 1, "volume": 0.1}]
    Engine._panel_capacity(eng, pos, acc, atrs)
    eng.store.system.lot_multiplier = 2.0
    Engine._panel_capacity(eng, pos, acc, atrs)
    assert eng.risk.capacity_calls == 2


def test_a_search_reuses_expired_capacity():
    """order_calc_margin shares the same lock the workers hold."""
    eng = _eng()
    acc = {"equity": 1000.0}
    atrs = {"GER40": 10.0}
    pos = [{"ticket": 1, "volume": 0.1}]
    Engine._panel_capacity(eng, pos, acc, atrs)
    eng.search_busy = lambda: True
    eng._capacity_cache_at = time.time() - 30.0
    Engine._panel_capacity(eng, pos, acc, atrs)
    assert eng.risk.capacity_calls == 1


def test_a_search_still_refreshes_opens_without_margin():
    """NAS100 closed then reopened while opt ran; US30 filled a new ticket.
    Capacity kept the 10:03 copy (6 opens, US30=0) because search busy
    skipped even a ticket-sig change. Open count and floating P/L do not
    need order_calc_margin — they come off the positions list snapshot
    already holds.
    """
    eng = _eng()
    acc = {"equity": 1000.0}
    atrs = {"GER40": 10.0}

    def _cap(positions, account, atrs, autopsies=None):
        eng.risk.capacity_calls += 1
        return {"rows": [{
            "symbol": "GER40", "broker_symbol": "GER40", "enabled": True,
            "open_positions": 1, "open_profit": 1.0,
            "free_slots": 2, "max_positions": 3,
            "margin_per_trade": 99.0,
        }], "open_total": 1, "global_free_slots": 12, "max_total_positions": 13}

    eng.risk.capacity = _cap
    first = [{"ticket": 1, "volume": 0.1, "symbol": "GER40",
              "profit": 1.0, "swap": 0.0, "magic": 1}]
    Engine._panel_capacity(eng, first, acc, atrs)
    eng.search_busy = lambda: True
    second = first + [{"ticket": 2, "volume": 0.1, "symbol": "GER40",
                       "profit": 2.0, "swap": 0.5, "magic": 1}]
    out = Engine._panel_capacity(eng, second, acc, atrs)
    assert eng.risk.capacity_calls == 1
    row = out["rows"][0]
    assert row["open_positions"] == 2
    assert row["open_profit"] == 3.5
    assert row["margin_per_trade"] == 99.0
    assert row["free_slots"] == 1
    assert out.get("search_frozen") is True
    assert out["open_total"] == 2
    assert out["global_free_slots"] == 11


def test_a_search_overlay_picks_up_an_enabled_flip():
    eng = _eng()
    acc = {"equity": 1000.0}
    atrs = {"GER40": 10.0}

    def _cap(positions, account, atrs, autopsies=None):
        eng.risk.capacity_calls += 1
        return {"rows": [{
            "symbol": "GER40", "enabled": True,
            "open_positions": 0, "open_profit": 0.0,
            "free_slots": 3, "max_positions": 3,
        }]}

    eng.risk.capacity = _cap
    Engine._panel_capacity(eng, [], acc, atrs)
    eng.search_busy = lambda: True
    eng.store.symbols["GER40"].enabled = False
    out = Engine._panel_capacity(eng, [], acc, atrs)
    assert eng.risk.capacity_calls == 1
    assert out["rows"][0]["enabled"] is False
    assert out["rows"][0]["free_slots"] == 0
