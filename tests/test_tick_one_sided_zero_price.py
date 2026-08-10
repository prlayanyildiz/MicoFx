"""tick(): a one-sided zero quote (bid<=0 XOR ask<=0) must be rejected too,
not just both-zero. A partial/glitched feed (illiquid instrument, rollover
gap) used to pass with only one side at zero, letting open_market() build an
order at price=0.0 and min_stop_distance() compute a nonsense spread from it.
"""
from __future__ import annotations

import threading

from micofx.mt5client import MT5Client


def _client_with_tick(bid, ask):
    client = object.__new__(MT5Client)
    client.connected = True
    client._lock = threading.Lock()
    client._tick_cache = {}
    client._broker_now = 0.0     # newest broker tick seen; see market_open()
    client.select = lambda symbol: symbol

    class _Tick:
        def __init__(self):
            self.bid = bid
            self.ask = ask
            self.time = 0

    class _MT5:
        @staticmethod
        def symbol_info_tick(symbol):
            return _Tick()

    return client, _MT5


def test_tick_rejects_zero_ask_with_positive_bid(monkeypatch):
    client, _MT5 = _client_with_tick(bid=1.1000, ask=0.0)
    monkeypatch.setattr("micofx.mt5client.mt5", _MT5)
    assert MT5Client.tick(client, "EURUSD") is None


def test_tick_rejects_zero_bid_with_positive_ask(monkeypatch):
    client, _MT5 = _client_with_tick(bid=0.0, ask=1.1002)
    monkeypatch.setattr("micofx.mt5client.mt5", _MT5)
    assert MT5Client.tick(client, "EURUSD") is None


def test_tick_rejects_both_sides_zero(monkeypatch):
    client, _MT5 = _client_with_tick(bid=0.0, ask=0.0)
    monkeypatch.setattr("micofx.mt5client.mt5", _MT5)
    assert MT5Client.tick(client, "EURUSD") is None


def test_tick_accepts_a_normal_quote(monkeypatch):
    client, _MT5 = _client_with_tick(bid=1.0998, ask=1.1000)
    monkeypatch.setattr("micofx.mt5client.mt5", _MT5)
    result = MT5Client.tick(client, "EURUSD")
    assert result is not None
    assert result["bid"] == 1.0998
    assert result["ask"] == 1.1000
