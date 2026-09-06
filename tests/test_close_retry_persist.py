"""Close-fail order_send backoff must survive soft-restart.

In-memory ``_close_retry_after`` alone re-arms a loud 10018/10031 attempt on
every restart (XAU #325114801 06.09 09:40). Persist next to weekend_pending.
"""
from __future__ import annotations

import threading
import types

from micofx import mt5client
from micofx.logbus import LOG
from micofx.mt5client import MT5Client

TICKET = 325114801


class _Pos:
    ticket = TICKET
    symbol = "XAUUSD"
    magic = 990021
    volume = 0.01
    type = 1
    price_open = 4429.73
    sl = 4439.05
    tp = 0.0
    profit = -1.5
    swap = 0.3


def _mt5(retcode: int, sends: list):
    class _MT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TIME_GTC = 0
        POSITION_TYPE_BUY = 0
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_DONE_PARTIAL = 10010
        TRADE_RETCODE_INVALID_FILL = 10030
        TRADE_RETCODE_MARKET_CLOSED = 10018
        TRADE_RETCODE_CONNECTION = 10031
        ORDER_FILLING_IOC = 1
        ORDER_FILLING_FOK = 2
        ORDER_FILLING_RETURN = 3

        @staticmethod
        def positions_get(**kwargs):
            return (_Pos(),)

        @staticmethod
        def order_send(request):
            sends.append(request)
            return types.SimpleNamespace(
                retcode=retcode, price=0.0, order=0, deal=0, volume=0.0,
                comment="fail")

        @staticmethod
        def last_error():
            return (0, "ok")

    return _MT5


def test_close_retry_persist_callback_fires(monkeypatch):
    sends: list = []
    persisted: list = []
    monkeypatch.setattr(mt5client, "mt5", _mt5(10018, sends))
    monkeypatch.setattr(mt5client, "_FILL_RETCODES", frozenset({10009, 10010}))
    monkeypatch.setattr(LOG, "emit", lambda *a, **k: None)
    clock = {"t": 1_700_000_000.0}
    monkeypatch.setattr(mt5client.time, "time", lambda: clock["t"])

    client = object.__new__(MT5Client)
    client.connected = True
    client._lock = threading.Lock()
    client.tick = lambda symbol: {"bid": 4431.0, "ask": 4431.2}
    client._filling = lambda symbol: 1
    client._persist_close_retry = lambda blob: persisted.append(dict(blob))

    assert MT5Client.close_position(client, TICKET) is False
    assert len(persisted) == 1
    assert TICKET in persisted[0]
    assert persisted[0][TICKET] == clock["t"] + mt5client.CLOSE_RETRY_BACKOFF_SEC
