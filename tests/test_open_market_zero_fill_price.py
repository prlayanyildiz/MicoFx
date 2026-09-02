"""MT5 market fills sometimes report result.price=0.

Re-anchoring off zero produced a negative BUY stop; modify_position then sent
sl=0, NO_CHANGES on an already-stopless ticket read as success, and the
position stayed naked. These tests pin the recovery.
"""
from __future__ import annotations

import threading
import time
import types

import pytest

from micofx.mt5client import MT5Client


class _Pos:
    def __init__(self, ticket, magic, price_open, volume=0.30, sl=0.0, tp=0.0):
        self.ticket = ticket
        self.magic = magic
        self.price_open = price_open
        self.volume = volume
        self.sl = sl
        self.tp = tp


REQUESTED = 25874.0
FILLED = 25874.0
SENT_SL = 25824.5
SL_DIST = REQUESTED - SENT_SL


def _make_client(*, modify_ok: bool = True):
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


def _mt5_stub(positions_by_call):
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
    monkeypatch.setattr(
        "micofx.mt5client._AMBIGUOUS_RETCODES",
        frozenset({mt5_cls.TRADE_RETCODE_TIMEOUT, mt5_cls.TRADE_RETCODE_CONNECTION}))


def test_zero_fill_price_resolves_open_and_keeps_sent_stop(monkeypatch):
    """When MT5 reports price=0 but fill matches the tick, skip bad re-anchor."""
    client = _make_client(modify_ok=True)
    pos = _Pos(4321, magic=7, price_open=FILLED, sl=SENT_SL)
    _install(monkeypatch, _mt5_stub([(), (pos,)]))
    out = MT5Client.open_market(
        client, "GER40", "buy", 0.30, SENT_SL, 0.0, magic=7)

    assert out["ok"] is True
    assert out["price"] == pytest.approx(FILLED)
    assert out["sl"] == pytest.approx(SENT_SL)
    assert out["sl"] > 0
    assert client.modifies == []


def test_zero_fill_price_slippage_reanchors_off_position_open(monkeypatch):
    slipped = REQUESTED + 20.0
    client = _make_client(modify_ok=True)
    pos = _Pos(4321, magic=7, price_open=slipped, sl=0.0)
    _install(monkeypatch, _mt5_stub([(), (pos,), (pos,)]))
    out = MT5Client.open_market(
        client, "GER40", "buy", 0.30, SENT_SL, 0.0, magic=7)

    assert out["ok"] is True
    assert out["price"] == pytest.approx(slipped)
    assert out["sl_tp_reanchored"] is True
    assert out["sl"] == pytest.approx(slipped - SL_DIST)
    assert client.modifies == [pytest.approx(slipped - SL_DIST)]


def test_zero_fill_price_refused_modify_keeps_sent_stop(monkeypatch):
    slipped = REQUESTED + 20.0
    client = _make_client(modify_ok=False)
    pos = _Pos(4321, magic=7, price_open=slipped, sl=SENT_SL)
    _install(monkeypatch, _mt5_stub([(), (pos,), (pos,)]))
    out = MT5Client.open_market(
        client, "GER40", "buy", 0.30, SENT_SL, 0.0, magic=7)

    assert out["ok"] is True
    assert out["sl_tp_reanchored"] is False
    assert out["sl"] == pytest.approx(SENT_SL)
    assert out["sl"] > 0
