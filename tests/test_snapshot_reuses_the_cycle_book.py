"""/api/state must not take a second positions_get on a fresh cycle.

The worker already refreshed Engine._positions at cycle start. snapshot()
used to call client.positions() again on every panel poll, sharing the
same MT5 lock. Empty is a valid flat book, so reuse must not use `or`.
"""
from __future__ import annotations

import time
from types import SimpleNamespace

from micofx.engine import Engine
from micofx.models import SymbolConfig


class _Client:
    def __init__(self):
        self.connected = True
        self.calls = 0
        self._next: list[dict] = []

    def positions(self):
        self.calls += 1
        return list(self._next)


def _eng() -> Engine:
    eng = object.__new__(Engine)
    eng.client = _Client()
    eng.store = SimpleNamespace(
        symbols={"GER40": SymbolConfig(symbol="GER40", magic=1, group="idx")},
        system=SimpleNamespace(poll_interval_sec=2.0),
    )
    eng._positions = []
    eng.    last_cycle_at = 0.0
    eng._account = {}
    eng._account_at = 0.0
    return eng


def test_a_fresh_flat_book_is_not_fetched_again():
    eng = _eng()
    eng.client._next = [{"ticket": 9, "magic": 1, "symbol": "GER40"}]
    eng._positions = []
    eng.last_cycle_at = time.time()

    out = Engine._panel_positions(eng)

    assert out == []
    assert eng.client.calls == 0


def test_a_never_cycled_engine_still_reads_the_broker():
    eng = _eng()
    eng.client._next = [{"ticket": 9, "magic": 1, "symbol": "GER40"}]

    out = Engine._panel_positions(eng)

    assert eng.client.calls == 1
    assert out[0]["ticket"] == 9
    assert out[0]["managed"] is True
    assert out[0]["config_symbol"] == "GER40"
    assert out[0]["group"] == "idx"


def test_a_stale_cycle_book_is_fetched_again():
    eng = _eng()
    eng.client._next = [{"ticket": 9, "magic": 1, "symbol": "GER40"}]
    eng._positions = [{"ticket": 1, "magic": 1, "symbol": "GER40"}]
    eng.last_cycle_at = time.time() - 30.0

    out = Engine._panel_positions(eng)

    assert eng.client.calls == 1
    assert out[0]["ticket"] == 9


def test_a_fresh_cycle_reuses_the_cached_account():
    """Panel poll must not take account_info when the cycle just did."""
    eng = _eng()
    eng._account = {"equity": 100.0, "balance": 100.0}
    eng._account_at = 0.0
    eng.last_cycle_at = time.time()
    eng.client.account = lambda: (_ for _ in ()).throw(
        AssertionError("account_info on a fresh cycle"))

    out = Engine._panel_account(eng)

    assert out["equity"] == 100.0


def test_a_stale_cycle_still_refreshes_the_account():
    eng = _eng()
    eng._account = {"equity": 1.0}
    eng._account_at = 0.0
    eng.last_cycle_at = time.time() - 30.0
    eng.client.account_calls = 0

    def _account():
        eng.client.account_calls += 1
        return {"equity": 9.0, "balance": 9.0}

    eng.client.account = _account
    eng._enforce_account_lock = lambda account: None

    out = Engine._panel_account(eng)

    assert eng.client.account_calls == 1
    assert out["equity"] == 9.0


def test_a_fresh_open_is_decorated_without_another_broker_read():
    eng = _eng()
    eng.client._next = [{"ticket": 99, "magic": 1, "symbol": "GER40"}]
    eng._positions = [{"ticket": 7, "magic": 1, "symbol": "GER40"}]
    eng.last_cycle_at = time.time()

    out = Engine._panel_positions(eng)

    assert eng.client.calls == 0
    assert out[0]["ticket"] == 7
    assert out[0]["managed"] is True
    assert out[0]["group"] == "idx"
    assert eng._positions[0] == {"ticket": 7, "magic": 1, "symbol": "GER40"}


def test_snapshot_uses_the_panel_account_helper():
    import inspect
    src = inspect.getsource(Engine.snapshot)
    assert "self._panel_account()" in src
    assert "self.refresh_account()" not in src
