"""close_position: positions_get(ticket) None must flip connected (not 'gone')."""
from __future__ import annotations

from micofx.mt5client import MT5Client


def test_close_position_ticket_lookup_none_flips_connected(monkeypatch):
    client = object.__new__(MT5Client)
    client.connected = True
    client._lock = __import__("threading").Lock()

    class _MT5:
        @staticmethod
        def positions_get(**kwargs):
            return None

        @staticmethod
        def last_error():
            return (-1, "fail")

    monkeypatch.setattr("micofx.mt5client.mt5", _MT5)

    ok = MT5Client.close_position(client, 42)

    assert ok is False
    assert client.connected is False
