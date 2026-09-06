"""Failed weekend closes must not hammer order_send every 2s poll.

Live 04–06.09: XAU #325114801 stuck over the weekend produced ~20k close
attempts (10018 / 10031). Log throttle (862ae49) quiets the ERROR storm but
still lets every poll call order_send. Connection / market-closed rejects
will not clear in two seconds — back off the send itself.
"""
from __future__ import annotations

import threading
import types

import pytest

from micofx import mt5client
from micofx.logbus import LOG
from micofx.mt5client import MT5Client

TICKET = 325114801


class _Pos:
    ticket = TICKET
    symbol = "XAUUSD"
    magic = 990021
    volume = 0.01
    type = 1  # SELL
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


def _client():
    c = object.__new__(MT5Client)
    c.connected = True
    c._lock = threading.Lock()
    c.tick = lambda symbol: {"bid": 4431.0, "ask": 4431.2}
    c._filling = lambda symbol: 1
    return c


@pytest.mark.parametrize("retcode", [10018, 10031])
def test_close_backs_off_order_send_after_market_or_link_fail(monkeypatch, retcode):
    sends: list = []
    monkeypatch.setattr(mt5client, "mt5", _mt5(retcode, sends))
    monkeypatch.setattr(mt5client, "_FILL_RETCODES", frozenset({10009, 10010}))
    monkeypatch.setattr(LOG, "emit", lambda *a, **k: None)
    clock = {"t": 1_000_000.0}
    monkeypatch.setattr(mt5client.time, "time", lambda: clock["t"])

    client = _client()
    assert MT5Client.close_position(client, TICKET) is False
    assert len(sends) == 1

    # Next poll ~2s later must not touch the broker again.
    clock["t"] += 2.0
    assert MT5Client.close_position(client, TICKET) is False
    assert len(sends) == 1

    # After the backoff window, one more attempt is allowed.
    clock["t"] += float(mt5client.CLOSE_RETRY_BACKOFF_SEC) + 0.1
    assert MT5Client.close_position(client, TICKET) is False
    assert len(sends) == 2


def test_close_success_clears_backoff(monkeypatch):
    sends: list = []
    monkeypatch.setattr(mt5client, "mt5", _mt5(10018, sends))
    monkeypatch.setattr(mt5client, "_FILL_RETCODES", frozenset({10009, 10010}))
    monkeypatch.setattr(LOG, "emit", lambda *a, **k: None)
    clock = {"t": 1_000_000.0}
    monkeypatch.setattr(mt5client.time, "time", lambda: clock["t"])
    client = _client()

    assert MT5Client.close_position(client, TICKET) is False
    assert len(sends) == 1

    # Flip broker to success and clear via a successful path after backoff.
    monkeypatch.setattr(mt5client, "mt5", _mt5(10009, sends))
    clock["t"] += float(mt5client.CLOSE_RETRY_BACKOFF_SEC) + 0.1
    assert MT5Client.close_position(client, TICKET) is True
    assert len(sends) == 2

    # Immediate retry after success would be a new close attempt (position
    # still mocked as open) — no leftover backoff from the old failure.
    n = len(sends)
    assert MT5Client.close_position(client, TICKET) is True
    assert len(sends) == n + 1
