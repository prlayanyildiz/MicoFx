"""Per-symbol close_all must not report flat when resolve() fails.

positions(symbol=...) returns [] on resolve miss WITHOUT flipping connected,
so close_all would otherwise return (0, 0) and the UI would show ok:true
while tickets under that magic may still be open.
"""
from __future__ import annotations

from micofx.mt5client import MT5Client


def test_close_all_symbol_resolve_miss_returns_remaining_unknown():
    client = object.__new__(MT5Client)
    client.connected = True
    client._name_map = {}
    client._overrides = {}

    def _ensure():
        return True

    def _resolve(symbol):
        return None

    def _positions(**kwargs):
        raise AssertionError("positions() must not be trusted after resolve miss")

    client.ensure = _ensure  # type: ignore[method-assign]
    client.resolve = _resolve  # type: ignore[method-assign]
    client.positions = _positions  # type: ignore[method-assign]

    closed, remaining = MT5Client.close_all(client, magics={1}, symbol="COPPER")

    assert closed == 0
    assert remaining == -1


def test_close_all_mid_call_positions_fail_returns_remaining_unknown():
    client = object.__new__(MT5Client)
    client.connected = True

    def _ensure():
        return True

    def _positions(**kwargs):
        client.connected = False
        return []

    client.ensure = _ensure  # type: ignore[method-assign]
    client.positions = _positions  # type: ignore[method-assign]

    closed, remaining = MT5Client.close_all(client, magics={1})

    assert closed == 0
    assert remaining == -1
