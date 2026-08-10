"""A failed SL re-anchor must report the stop the broker actually holds.

open_market builds SL/TP from the pre-fill tick, then - when the fill slipped -
recomputes them off the real fill price and pushes the correction. If that
modify is refused, the broker keeps the levels that were originally sent.

Returning the *intended* levels anyway put a stop in the TRADE log that exists
nowhere on the broker: the log would say the trade risked what it was sized
for while the live position risked the pre-fill distance. Reconstructing why a
trade gave back more than 1R, that log lies.

_verify_ambiguous_send's recovery path already reverted on a refused modify and
says so in its own comment; the normal fill path is the one that did not.
"""
from __future__ import annotations

import threading
import time
import types

import pytest

from micofx.mt5client import MT5Client


class _Pos:
    def __init__(self, ticket, magic, price_open=1.1000, volume=0.10,
                 sl=1.0950, tp=0.0):
        self.ticket = ticket
        self.magic = magic
        self.price_open = price_open
        self.volume = volume
        self.sl = sl
        self.tp = tp


# The order is built off ask=1.1000 and fills 20 points away at 1.1020, which
# is well past the min_stop_distance*0.1 threshold that arms the re-anchor.
REQUESTED = 1.1000
FILLED = 1.1020
SENT_SL = 1.0950              # requested - 50 points
REANCHORED_SL = 1.0970        # filled - the same 50 points


def _make_client(modify_ok: bool):
    client = object.__new__(MT5Client)
    client.connected = True
    client._lock = threading.Lock()
    client.select = lambda symbol: symbol
    client.tick = lambda symbol: {"ask": REQUESTED, "bid": REQUESTED - 0.0002}
    client.normalize_volume = lambda symbol, volume: volume
    client.normalize_price = lambda symbol, price: round(price, 5)
    client.min_stop_distance = lambda symbol: 0.0010
    client._filling = lambda symbol: 1
    client.modifies = []

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
                retcode=10009, price=FILLED, order=4321, deal=99,
                volume=0.10, comment="done")

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


def _open(client, monkeypatch):
    # before-send snapshot flat, then the filled position resolvable by ticket.
    _install(monkeypatch, _mt5_stub([(), (_Pos(4321, magic=7),)]))
    return MT5Client.open_market(client, "EURUSD", "buy", 0.10, SENT_SL, 0.0, magic=7)


def test_refused_reanchor_reports_the_level_the_broker_kept(monkeypatch):
    client = _make_client(modify_ok=False)
    out = _open(client, monkeypatch)

    assert out["ok"] is True
    assert out["sl_tp_reanchored"] is False
    # The correction was attempted...
    assert client.modifies == [pytest.approx(REANCHORED_SL)]
    # ...and refused, so the reported stop is the one actually on the broker.
    assert out["sl"] == pytest.approx(SENT_SL)
    assert out["sl"] != pytest.approx(REANCHORED_SL)


def test_accepted_reanchor_reports_the_corrected_level(monkeypatch):
    client = _make_client(modify_ok=True)
    out = _open(client, monkeypatch)

    assert out["sl_tp_reanchored"] is True
    assert out["sl"] == pytest.approx(REANCHORED_SL)


def test_unresolvable_ticket_reports_the_sent_level(monkeypatch):
    # Neither the deal, the order ticket, nor the symbol-wide fallback resolves
    # a position - no modify is even attempted, so the broker still holds the
    # levels that went out with the order.
    client = _make_client(modify_ok=True)
    _install(monkeypatch, _mt5_stub([(), (), ()]))
    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, SENT_SL, 0.0, magic=7)

    assert out["ok"] is True
    assert out["position"] == 0
    assert out["sl_tp_reanchored"] is False
    assert client.modifies == []
    assert out["sl"] == pytest.approx(SENT_SL)


def test_recovery_path_still_reverts_the_same_way(monkeypatch):
    # The behaviour this fix mirrors, pinned so the two paths cannot drift
    # apart again: an adopted position whose re-anchor is refused reports the
    # stop the broker is holding, not the one we wanted.
    client = _make_client(modify_ok=False)
    adopted = _Pos(4321, magic=7, price_open=FILLED, sl=SENT_SL)
    _install(monkeypatch, _mt5_stub([(adopted,)]))

    out = MT5Client._verify_ambiguous_send(
        client, "EURUSD", "EURUSD", 7, set(), REQUESTED, "timeout",
        side="buy", req_sl=SENT_SL, req_tp=0.0)

    assert out["ok"] is True
    assert out["position"] == 4321
    assert out["sl_tp_reanchored"] is False
    assert client.modifies == [pytest.approx(REANCHORED_SL)]
    assert out["sl"] == pytest.approx(SENT_SL)
