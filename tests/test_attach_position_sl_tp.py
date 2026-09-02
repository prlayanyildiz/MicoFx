"""Book-wide hard-stop attach after a stopless fill."""
from __future__ import annotations

import threading
import time
import types

import pytest

from micofx.mt5client import MT5Client


class _Pos:
    def __init__(self, ticket, magic, price_open, sl=0.0, tp=0.0, volume=0.30):
        self.ticket = ticket
        self.magic = magic
        self.price_open = price_open
        self.sl = sl
        self.tp = tp
        self.volume = volume


REQUESTED = 25874.0
SENT_SL = 25824.5


def _client(*, modify_ok: bool = True):
    client = object.__new__(MT5Client)
    client.connected = True
    client._lock = threading.Lock()
    client.select = lambda symbol: symbol
    client.tick = lambda symbol: {"ask": REQUESTED, "bid": REQUESTED - 1.0}
    client.normalize_volume = lambda symbol, volume: volume
    client.normalize_price = lambda symbol, price: round(price, 2)
    client.min_stop_distance = lambda symbol: 1.0
    client._filling = lambda symbol: 1
    client.modifies: list[float] = []

    def modify_position(ticket, sl, tp, symbol):
        client.modifies.append(sl)
        return modify_ok

    client.modify_position = modify_position
    return client


def _mt5(positions_by_call):
    calls = {"n": 0}

    class _MT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TIME_GTC = 0
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_DONE_PARTIAL = 10010

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
            return types.SimpleNamespace(
                retcode=10009, price=0.0, order=4321, deal=99,
                volume=0.30, comment="done")

        @staticmethod
        def last_error():
            return (0, "ok")

    return _MT5


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _s: None)


def _install(monkeypatch, mt5_cls):
    monkeypatch.setattr("micofx.mt5client.mt5", mt5_cls)
    monkeypatch.setattr(
        "micofx.mt5client._FILL_RETCODES",
        frozenset({mt5_cls.TRADE_RETCODE_DONE, mt5_cls.TRADE_RETCODE_DONE_PARTIAL}))


def test_verify_attaches_stop_when_fill_matches_tick_but_broker_is_stopless(monkeypatch):
    client = _client(modify_ok=True)
    adopted = _Pos(4321, magic=7, price_open=REQUESTED, sl=0.0)
    _install(monkeypatch, _mt5([(adopted,)]))
    out = MT5Client._verify_ambiguous_send(
        client, "GER40", "GER40", 7, set(), REQUESTED, "timeout",
        side="buy", req_sl=SENT_SL, req_tp=0.0)

    assert out["ok"] is True
    assert out["sl_tp_reanchored"] is True
    assert out["sl"] == pytest.approx(SENT_SL)
    assert client.modifies == [pytest.approx(SENT_SL)]


def test_attach_position_sl_tp_clamps_buy_stop_to_live_bid(monkeypatch):
    client = _client(modify_ok=True)
    client.tick = lambda symbol: {"ask": REQUESTED, "bid": 25870.0}
    too_tight_sl = REQUESTED - 1.0
    sl, tp, ok = MT5Client.attach_position_sl_tp(
        client, "GER40", 99, "buy", REQUESTED, too_tight_sl, 0.0,
        anchor_price=REQUESTED)

    assert ok is True
    assert sl == pytest.approx(25869.0)
    assert client.modifies == [pytest.approx(25869.0)]
