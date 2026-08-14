"""order_send timeout / None must never be reported as a plain rejection.

The request is already on the wire when the terminal gives up waiting, so the
broker may have filled it. Calling that a failure let the caller keep the
signal alive and fire a second order_send on the next poll - a duplicate
position on top of a fill nobody knew about. These cover the three outcomes
``_verify_ambiguous_send`` has to tell apart.
"""
from __future__ import annotations

import threading
import time
import types

import pytest

from micofx.engine import Engine
from micofx.mt5client import MT5Client


class _Pos:
    def __init__(self, ticket, magic, price_open=1.1000, volume=0.10, sl=1.0950, tp=1.1050):
        self.ticket = ticket
        self.magic = magic
        self.price_open = price_open
        self.volume = volume
        self.sl = sl
        self.tp = tp


def _make_client():
    client = object.__new__(MT5Client)
    client.connected = True
    client._lock = threading.Lock()
    client.select = lambda symbol: symbol
    client.tick = lambda symbol: {"ask": 1.1000, "bid": 1.0998}
    client.normalize_volume = lambda symbol, volume: volume
    client.normalize_price = lambda symbol, price: price
    client.min_stop_distance = lambda symbol: 0.0001
    client._filling = lambda symbol: 1
    client.modify_position = lambda *a, **k: True
    return client


def _mt5_stub(send, positions_by_call):
    """positions_by_call: list of return values for successive positions_get."""
    calls = {"n": 0}

    class _MT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TIME_GTC = 0
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_DONE_PARTIAL = 10010
        TRADE_RETCODE_TIMEOUT = 10012
        TRADE_RETCODE_INVALID_STOPS = 10016
        TRADE_RETCODE_INVALID_FILL = 10030
        TRADE_RETCODE_CONNECTION = 10031

        @staticmethod
        def positions_get(**kwargs):
            idx = min(calls["n"], len(positions_by_call) - 1)
            calls["n"] += 1
            return positions_by_call[idx]

        @staticmethod
        def history_deals_get(**kwargs):
            return ()

        @staticmethod
        def order_send(request):
            return send(request)

        @staticmethod
        def last_error():
            return (-10005, "IPC timeout")

    return _MT5, calls


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _s: None)


def _install(monkeypatch, mt5_cls):
    monkeypatch.setattr("micofx.mt5client.mt5", mt5_cls)
    monkeypatch.setattr(
        "micofx.mt5client._FILL_RETCODES",
        frozenset({mt5_cls.TRADE_RETCODE_DONE, mt5_cls.TRADE_RETCODE_DONE_PARTIAL}),
    )
    monkeypatch.setattr(
        "micofx.mt5client._AMBIGUOUS_RETCODES",
        frozenset({mt5_cls.TRADE_RETCODE_TIMEOUT, mt5_cls.TRADE_RETCODE_CONNECTION}),
    )


def test_none_result_but_position_opened_is_adopted_not_retried(monkeypatch):
    """order_send returns None, yet the fill is really there: report success."""
    client = _make_client()
    sends = {"n": 0}

    def order_send(request):
        sends["n"] += 1
        return None

    mt5_cls, _ = _mt5_stub(order_send, [
        (),                             # before-send snapshot: flat
        (_Pos(4321, magic=7),),         # verification: the fill did land
    ])
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is True
    assert out["recovered"] is True
    assert out["position"] == 4321
    assert out["volume"] == 0.10
    # Exactly one send - the whole point is that no second order goes out.
    assert sends["n"] == 1
    assert client.connected is True


def test_timeout_retcode_with_no_new_position_is_a_plain_retryable_failure(monkeypatch):
    client = _make_client()
    result = types.SimpleNamespace(retcode=10012, price=0.0, order=0, deal=0, volume=0.0,
                                   comment="timeout")

    mt5_cls, _ = _mt5_stub(lambda request: result, [
        (),   # before-send snapshot
        (),   # every verification read: still flat -> order never reached market
    ])
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is False
    # Not flagged ambiguous: verified as "never filled", so a retry is safe.
    assert not out.get("ambiguous")
    assert client.connected is True
    # Engine.LINK_BACKOFF keys off retcode and verified_unfilled: without
    # them a 10012/10031 storm re-runs the 2.1s verifier every poll.
    assert out.get("retcode") == 10012
    assert out.get("verified_unfilled") is True


def test_connection_retcode_verified_flat_forwards_retcode(monkeypatch):
    """The 10031 storm path must carry retcode out of the verifier."""
    client = _make_client()
    result = types.SimpleNamespace(retcode=10031, price=0.0, order=0, deal=0, volume=0.0,
                                   comment="no network")

    mt5_cls, _ = _mt5_stub(lambda request: result, [
        (),
        (),
    ])
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is False
    assert not out.get("ambiguous")
    assert out.get("retcode") == 10031
    assert out.get("verified_unfilled") is True
    assert "olusmamis" in out["error"]


def test_order_send_none_verified_flat_still_marks_unfilled(monkeypatch):
    """IPC/None is outside AMBIGUOUS_RETCODES - flag must still arm the park."""
    client = _make_client()

    mt5_cls, _ = _mt5_stub(lambda request: None, [
        (),
        (),
    ])
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is False
    assert not out.get("ambiguous")
    assert out.get("verified_unfilled") is True
    # last_error from the stub is an IPC code, not 10031/10012
    assert out.get("retcode") not in (10012, 10031)


def test_timeout_with_unreadable_position_book_is_ambiguous(monkeypatch):
    client = _make_client()
    result = types.SimpleNamespace(retcode=10012, price=0.0, order=0, deal=0, volume=0.0,
                                   comment="timeout")

    mt5_cls, _ = _mt5_stub(lambda request: result, [
        (),     # before-send snapshot succeeds
        None,   # verification cannot read the book
    ])
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is False
    assert out["ambiguous"] is True
    assert client.connected is False


def test_timeout_with_two_new_tickets_is_ambiguous_not_a_guess(monkeypatch):
    client = _make_client()
    result = types.SimpleNamespace(retcode=10012, price=0.0, order=0, deal=0, volume=0.0,
                                   comment="timeout")

    mt5_cls, _ = _mt5_stub(lambda request: result, [
        (),                                              # before: flat
        (_Pos(1, magic=7), _Pos(2, magic=7)),            # two new -> cannot attribute
    ])
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is False
    assert out["ambiguous"] is True


def test_pre_existing_ticket_is_not_mistaken_for_the_new_fill(monkeypatch):
    """A same-magic position that was already open must not be adopted."""
    client = _make_client()
    existing = _Pos(900, magic=7)

    mt5_cls, _ = _mt5_stub(lambda request: None, [
        (existing,),   # before-send: this ticket already existed
        (existing,),   # verification: nothing new appeared
    ])
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is False
    assert not out.get("ambiguous")
    assert "olusmamis" in out["error"]
    assert out.get("verified_unfilled") is True
    """An ambiguous send must not be re-offered on the next poll.

    The signal chain is what keeps an entry pending until the bar rolls over;
    leaving it standing after an unresolvable send is precisely how a possibly
    -filled order gets a second order_send fired at it.
    """
    engine, client, state, cfg = _entry_harness(
        {"ok": False, "ambiguous": True, "error": "emir sonucu belirsiz"})

    engine._try_entry(cfg, state, account={"balance": 1000.0})

    assert client.open_market_calls == 1
    assert state.signal == ""
    assert state.signal_source == ""
    assert state.primary_signal == ""
    assert state.pending_bar_key == (0, 0)
    assert "belirsiz" in state.note
    # An empty state.signal is what _cycle() checks before it ever calls
    # _try_entry again, so a cleared chain is the same "will not be re-offered"
    # guarantee the NON_RETRYABLE_RETCODES path already relies on.


def test_engine_still_retries_an_ordinary_reject():
    """Guard against over-correcting: a plain reject stays retryable."""
    engine, client, state, cfg = _entry_harness(
        {"ok": False, "retcode": 10004, "error": "requote"})

    engine._try_entry(cfg, state, account={"balance": 1000.0})

    assert state.signal == "buy"          # still pending for the next poll
    assert state.pending_bar_key != (0, 0) or state.signal == "buy"
    assert "EURUSD" not in engine._link_backoff


def test_engine_parks_after_verified_connection_refusal():
    """Storm path: book readable, nothing filled, retcode 10031 -> 30s park.

    Signal stays (delayed, not dropped) - that is the distinction from
    ambiguous. Without retcode/verified_unfilled on the open_market dict
    the park never armed.
    """
    from micofx.engine import LINK_BACKOFF_SEC

    engine, client, state, cfg = _entry_harness({
        "ok": False,
        "retcode": 10031,
        "verified_unfilled": True,
        "error": "EURUSD: emir sonucu belirsiz (10031 no network) - "
                 "dogrulandi: yeni pozisyon olusmamis, emir gecmemis",
    })

    engine._try_entry(cfg, state, account={"balance": 1000.0})

    assert state.signal == "buy"
    assert state.pending_bar_key != (0, 0)
    until = engine._link_backoff.get("EURUSD", 0.0)
    assert until > time.time()
    assert until <= time.time() + LINK_BACKOFF_SEC + 1.0

    # Next poll hits the gate and does not re-enter open_market.
    client.open_market_calls = 0
    engine._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == 0
    assert state.entry_block == "baglanti_beklemede"


def test_engine_parks_ipc_verified_flat_without_ambiguous_retcode():
    """order_send None / IPC last_error is not in AMBIGUOUS_RETCODES."""
    engine, client, state, cfg = _entry_harness({
        "ok": False,
        "retcode": -10001,
        "verified_unfilled": True,
        "error": "EURUSD: order_send bos dondu (-10001: IPC) - "
                 "dogrulandi: yeni pozisyon olusmamis, emir gecmemis",
    })

    engine._try_entry(cfg, state, account={"balance": 1000.0})

    assert engine._link_backoff.get("EURUSD", 0.0) > time.time()
    assert state.signal == "buy"


# --------------------------------------------------------------- engine harness

def _entry_harness(open_market_result):
    """Minimal Engine wired to a client whose open_market returns a fixed dict."""
    from micofx.engine import SymbolState
    from micofx.models import SymbolConfig
    from micofx.risk import Verdict

    class _Client:
        def __init__(self):
            self.open_market_calls = 0
            self.connected = True

        def min_stop_distance(self, symbol):
            return 0.0001

        def tick(self, symbol):
            return {"ask": 1.1000, "bid": 1.0998, "spread": 0.0002}

        def server_now(self):
            return time.time()

        def open_market(self, *a, **kw):
            self.open_market_calls += 1
            return dict(open_market_result)

        def positions(self):
            return []

        def info(self, symbol):
            return {"point": 0.0001}

        def money_per_price_unit(self, symbol, volume):
            return 1.0

    class _Risk:
        def lot_for(self, cfg, sl_distance, balance, ai_scale=1.0):
            return 0.1, "ok"

        def can_open(self, cfg, side, lot, positions, account, sec_tickets=frozenset()):
            return Verdict(ok=True)

    class _Store:
        def __init__(self, cfg):
            self.system = types.SimpleNamespace(
                slippage_points=5, block_high_cost=False, max_cost_pct_of_risk=0.0,
                trade_all_hours=True, daily_loss_flatten=False, day_end_flatten_min=0)
            self.symbols = types.SimpleNamespace(get=lambda s: cfg)
            self.settings: dict = {}

        def opt_params(self):
            return {}

        def set_setting(self, key, value):
            self.settings[key] = value

    cfg = SymbolConfig(symbol="EURUSD", group="crypto", magic=1)
    client = _Client()
    eng = object.__new__(Engine)
    eng.store = _Store(cfg)
    eng.client = client
    eng.risk = _Risk()
    eng.supervisor = types.SimpleNamespace(gate=lambda cfg, now: (True, "", 1.0))
    eng.execution = types.SimpleNamespace(record=lambda *a, **kw: None)
    eng.entry_lock = threading.Lock()
    eng._positions = []
    eng._sec_tickets = set()
    eng._sec_cfgs = {}
    eng._orphan_tickets = set()
    eng._orphan_scan = {}
    eng._link_backoff = {}   # real Engine always has it
    eng.states = {}

    state = SymbolState("EURUSD")
    state.signal = "buy"
    state.signal_source = "primary"
    state.primary_signal = "buy"
    state.pending_bar_key = (1, 1)
    state.atr = 0.001
    return eng, client, state, cfg

