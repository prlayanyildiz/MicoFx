"""A failed SL/TP modify must name the broker/IPC error, not a fake retcode.

Live 17.08: ``SL/TP guncellenemedi #359440001 (0)``. ``order_send`` returning
None is not retcode 0 - ``getattr(result, "retcode", 0)`` invents that number
and ``mt5.last_error()`` (the actual reason) never reaches the log. The next
bar cannot be diagnosed from ``(0)``.
"""
from __future__ import annotations

import threading
import types

from micofx.logbus import LOG
from micofx.mt5client import MT5Client

TICKET = 359440001


def _client() -> MT5Client:
    client = object.__new__(MT5Client)
    client._lock = threading.Lock()
    client.resolve = lambda symbol: symbol
    client.normalize_price = lambda symbol, price: round(float(price), 1)
    return client


def _mt5(*, send, last_error=(-10001, "IPC send failed")):
    class _MT5:
        TRADE_ACTION_SLTP = 6
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_NO_CHANGES = 10025

        @staticmethod
        def order_send(request):
            return send(request)

        @staticmethod
        def last_error():
            return last_error

    return _MT5


def _warns() -> list[str]:
    return [
        e["message"] for e in LOG.recent()
        if e["level"] == "WARN" and f"#{TICKET}" in e["message"]
    ]


def test_modify_none_logs_last_error_not_a_fake_zero(monkeypatch):
    monkeypatch.setattr("micofx.mt5client.mt5", _mt5(send=lambda req: None))
    before = len(_warns())
    ok = MT5Client.modify_position(_client(), TICKET, 69050.0, 0.0, "JPN225")
    assert ok is False
    lines = _warns()[before:]
    assert lines, "a None modify must warn"
    msg = lines[0]
    assert "(0)" not in msg, msg
    assert "last_error" in msg, msg
    assert "-10001" in msg, msg
    assert "IPC send failed" in msg, msg


def test_the_same_ticket_and_reason_warns_once(monkeypatch):
    monkeypatch.setattr("micofx.mt5client.mt5", _mt5(send=lambda req: None))
    client = _client()
    before = len(_warns())
    MT5Client.modify_position(client, TICKET, 69050.0, 0.0, "JPN225")
    MT5Client.modify_position(client, TICKET, 69050.0, 0.0, "JPN225")
    assert len(_warns()[before:]) == 1


def test_a_new_reason_warns_again(monkeypatch):
    errors = [(-10001, "IPC send failed"), (-10005, "IPC timeout")]

    class _MT5:
        TRADE_ACTION_SLTP = 6
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_NO_CHANGES = 10025

        @staticmethod
        def order_send(request):
            return None

        @staticmethod
        def last_error():
            return errors[0]

    monkeypatch.setattr("micofx.mt5client.mt5", _MT5)
    client = _client()
    before = len(_warns())
    MT5Client.modify_position(client, TICKET, 69050.0, 0.0, "JPN225")
    errors[0] = errors[1]
    MT5Client.modify_position(client, TICKET, 69050.0, 0.0, "JPN225")
    lines = _warns()[before:]
    assert len(lines) == 2
    assert "-10001" in lines[0]
    assert "-10005" in lines[1]


def test_a_rejected_result_logs_comment_and_retcode(monkeypatch):
    def send(request):
        return types.SimpleNamespace(
            retcode=10016, comment="Invalid stops",
            request=request,
        )

    monkeypatch.setattr("micofx.mt5client.mt5", _mt5(send=send))
    before = len(_warns())
    MT5Client.modify_position(_client(), TICKET, 69050.0, 0.0, "JPN225")
    msg = _warns()[before:][0]
    assert "10016" in msg
    assert "Invalid stops" in msg


def test_no_changes_is_still_silent(monkeypatch):
    def send(request):
        return types.SimpleNamespace(retcode=10025, comment="No changes")

    monkeypatch.setattr("micofx.mt5client.mt5", _mt5(send=send))
    before = len(_warns())
    ok = MT5Client.modify_position(_client(), TICKET, 69039.6, 0.0, "JPN225")
    assert ok is False
    assert _warns()[before:] == []


def test_pepperstone_done_zero_is_success_not_a_warning(monkeypatch):
    """Live 17.08 09:40: retcode=0 comment=Done, SL actually moved to 69062.

    Today's check only accepts TRADE_RETCODE_DONE (10009), so this warns and
    returns False — the engine then leaves its book on the old SL.
    """
    def send(request):
        return types.SimpleNamespace(retcode=0, comment="Done", request=request)

    monkeypatch.setattr("micofx.mt5client.mt5", _mt5(send=send))
    client = _client()
    before = len(_warns())
    ok = MT5Client.modify_position(client, TICKET, 69062.0, 0.0, "JPN225")
    assert ok is True
    assert _warns()[before:] == []


def test_a_bare_zero_without_done_is_still_a_failure(monkeypatch):
    def send(request):
        return types.SimpleNamespace(retcode=0, comment="", request=request)

    monkeypatch.setattr(
        "micofx.mt5client.mt5",
        _mt5(send=send, last_error=(1, "Success")),
    )
    before = len(_warns())
    ok = MT5Client.modify_position(_client(), TICKET, 69062.0, 0.0, "JPN225")
    assert ok is False
    assert _warns()[before:], "retcode=0 without comment=Done must still warn"

