"""_try_entry: secondary fill whose broker ticket cannot be resolved.

open_market() can report ok=True with position=None (the fill's ticket could
not be read back). engine._try_entry then diffs same-magic positions before/
after the fill to find the new ticket. This covers the two ambiguous cases:
zero new tickets, and more than one - neither is the ordinary "exactly one
candidate" path that closes it and retries cleanly.
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig
from micofx.risk import Verdict


class _FakeClient:
    def __init__(self, positions_after):
        self._positions_after = positions_after
        self.closed: list[int] = []
        self.close_ok: set[int] = set()

    def min_stop_distance(self, symbol):
        return 0.0001

    def tick(self, symbol):
        return {"ask": 1.1000, "bid": 1.0998, "spread": 0.0002}

    def server_now(self):
        import time
        return time.time()

    def open_market(self, symbol, side, lot, sl, tp, magic, slippage=0, comment=""):
        return {"ok": True, "position": None, "requested": 1.1000, "price": 1.1000,
                "volume": lot, "sl": sl, "tp": tp, "partial_fill": False,
                "sl_tp_reanchored": True}

    def positions(self):
        return self._positions_after

    def close_position(self, ticket, slippage_points, comment):
        self.closed.append(ticket)
        return ticket in self.close_ok

    def info(self, symbol):
        return {"point": 0.0001}

    def money_per_price_unit(self, symbol, volume):
        return 1.0


class _FakeRisk:
    def lot_for(self, cfg, sl_distance, balance, ai_scale=1.0):
        return 0.1, "ok"

    def can_open(self, cfg, side, lot, positions, account, sec_tickets=frozenset()):
        return Verdict(ok=True)


class _FakeSupervisor:
    def gate(self, cfg, server_now):
        return True, "", 1.0


class _FakeExecution:
    def record(self, *a, **kw):
        pass


class _FakeSymbols:
    def __init__(self, cfg):
        self._cfg = cfg

    def get(self, symbol):
        return self._cfg


class _FakeStore:
    def __init__(self, cfg):
        self.system = SimpleNamespace(slippage_points=5, block_high_cost=False,
                                       max_cost_pct_of_risk=0.0, trade_all_hours=True)
        self.symbols = _FakeSymbols(cfg)

    def opt_params(self):
        return {}

    def set_setting(self, key, value):
        pass


def _make_engine(cfg, positions_after):
    client = _FakeClient(positions_after)
    store = _FakeStore(cfg)
    eng = object.__new__(Engine)
    eng.store = store
    eng.client = client
    eng.risk = _FakeRisk()
    eng.supervisor = _FakeSupervisor()
    eng.execution = _FakeExecution()
    eng.entry_lock = threading.Lock()
    eng._positions = []
    eng._sec_tickets = set()
    eng._sec_cfgs = {}
    eng.states = {}
    return eng, client


def _cfg():
    # crypto group so weekend_closed() never blocks the test regardless of
    # the day this runs on.
    return SymbolConfig(symbol="EURUSD", group="crypto", magic=1,
                        secondary_strategy="micro_rev", secondary_timeframe="M5",
                        ensemble_enabled=True)


def _state():
    st = SymbolState("EURUSD")
    st.signal = "buy"
    st.signal_source = "secondary"
    st.sec_atr = 0.001
    return st


def test_secondary_unresolved_ticket_zero_candidates_does_not_report_success():
    cfg = _cfg()
    # open_market reports ok, but positions() afterward shows nothing new for
    # this magic - zero candidates.
    eng, client = _make_engine(cfg, positions_after=[])
    state = _state()

    eng._try_entry(cfg, state, account={"balance": 1000.0})

    assert client.closed == []
    assert "cozulemedi" in state.note
    # Not treated as a successful fill: no cooldown, no signal-clear.
    assert state.cooldown_until == 0.0
    assert state.signal == "buy"


def test_secondary_unresolved_ticket_multiple_candidates_closes_all():
    cfg = _cfg()
    # Two same-magic tickets appear after the fill - ambiguous, both are
    # closed for safety.
    eng, client = _make_engine(cfg, positions_after=[
        {"ticket": 101, "magic": 1}, {"ticket": 102, "magic": 1},
    ])
    client.close_ok = {101, 102}
    state = _state()

    eng._try_entry(cfg, state, account={"balance": 1000.0})

    assert set(client.closed) == {101, 102}
    assert "cozulemedi" in state.note
    # Both closed cleanly -> treated like a failed entry, safe to retry.
    assert state.cooldown_until == 0.0
    assert state.signal == ""
    assert state.pending_bar_key == (0, 0)


def test_secondary_unresolved_ticket_multiple_candidates_partial_close_failure():
    cfg = _cfg()
    eng, client = _make_engine(cfg, positions_after=[
        {"ticket": 201, "magic": 1}, {"ticket": 202, "magic": 1},
    ])
    client.close_ok = {201}  # 202 fails to close

    state = _state()
    eng._try_entry(cfg, state, account={"balance": 1000.0})

    assert set(client.closed) == {201, 202}
    assert "cozulemedi" in state.note
    # Not all resolved: must not look like a normal successful fill.
    assert state.cooldown_until == 0.0
    assert state.signal == "buy"
