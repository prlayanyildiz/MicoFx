"""open_market: positions_get(ticket=candidate) None must flip connected
(not be treated as "candidate ticket not found" and fall through to the
symbol-wide lookup)."""
from __future__ import annotations

import threading
import types

from micofx.mt5client import MT5Client


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


def test_open_market_candidate_lookup_none_flips_connected(monkeypatch):
    client = _make_client()

    result = types.SimpleNamespace(
        retcode=None, price=1.1000, order=555, deal=999, volume=0.10,
    )

    class _MT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TIME_GTC = 0
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_DONE_PARTIAL = 10010
        TRADE_RETCODE_INVALID_STOPS = 10016
        TRADE_RETCODE_INVALID_FILL = 10030

        @staticmethod
        def positions_get(**kwargs):
            # symbol-scoped "before" snapshot succeeds; the ticket-scoped
            # "after" lookup (the candidate check) is the one that fails.
            if "symbol" in kwargs:
                return ()
            if "ticket" in kwargs:
                return None
            raise AssertionError(f"unexpected positions_get kwargs: {kwargs}")

        @staticmethod
        def history_deals_get(**kwargs):
            return ()

        @staticmethod
        def order_send(request):
            result.retcode = _MT5.TRADE_RETCODE_DONE
            return result

        @staticmethod
        def last_error():
            return (-1, "fail")

    monkeypatch.setattr("micofx.mt5client.mt5", _MT5)
    monkeypatch.setattr(
        "micofx.mt5client._FILL_RETCODES",
        frozenset({_MT5.TRADE_RETCODE_DONE, _MT5.TRADE_RETCODE_DONE_PARTIAL}),
    )

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=1)

    assert out["ok"] is True
    assert out["position"] == 0
    assert client.connected is False
