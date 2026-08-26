"""``kar=`` on a MicoFX-sent close must mean the same thing as on a stop exit.

positions_get's ``profit`` is the *floating* figure read a moment before the
order went out, and carries no commission. Logging it as ``kar=`` reported
neither the price the close actually got nor the full cost of the round trip -
while the broker-side exit path (ExecutionMonitor.reap) reports true realised
P/L under that same label. Two lines in one log wearing the same label were
different quantities, and the log is what gets reconciled against the balance.

The lookup runs only after the close has already succeeded, so it can never
hold up a flatten or a panic; when history has not caught up the line falls
back and says so rather than quietly printing the other quantity.
"""
from __future__ import annotations

import threading
import types

import pytest

from micofx.logbus import LOG
from micofx.mt5client import MT5Client

TICKET = 4242
ORDER = 777


class _Pos:
    ticket = TICKET
    symbol = "NAS100"
    magic = 7
    volume = 0.3
    type = 0                 # POSITION_TYPE_BUY
    price_open = 29778.6
    sl = 29725.2
    tp = 0.0
    profit = -12.90          # floating, pre-close, no commission
    swap = -0.40


def _deal(position=TICKET, profit=-13.10, commission=-0.50, swap=-0.40):
    return types.SimpleNamespace(position_id=position, profit=profit,
                                 commission=commission, swap=swap)


def _mt5(deals, send_retcode=10009):
    class _MT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        ORDER_TIME_GTC = 0
        POSITION_TYPE_BUY = 0
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_DONE_PARTIAL = 10010
        TRADE_RETCODE_INVALID_FILL = 10030
        ORDER_FILLING_IOC = 1
        ORDER_FILLING_FOK = 2
        ORDER_FILLING_RETURN = 3

        @staticmethod
        def positions_get(**kwargs):
            return (_Pos(),)

        @staticmethod
        def order_send(request):
            return types.SimpleNamespace(retcode=send_retcode, price=29725.0,
                                         order=ORDER, deal=99, volume=0.3,
                                         comment="done")

        @staticmethod
        def history_deals_get(**kwargs):
            if isinstance(deals, Exception):
                raise deals
            return deals

        @staticmethod
        def last_error():
            return (0, "ok")

    return _MT5


def _client():
    c = object.__new__(MT5Client)
    c.connected = True
    c._lock = threading.Lock()
    c.tick = lambda symbol: {"bid": 29725.0, "ask": 29725.2}
    c._filling = lambda symbol: 1
    return c


def _close(monkeypatch, deals):
    monkeypatch.setattr("micofx.mt5client.mt5", _mt5(deals))
    monkeypatch.setattr("micofx.mt5client._FILL_RETCODES", frozenset({10009, 10010}))
    lines: list[str] = []
    monkeypatch.setattr(LOG, "emit",
                        lambda msg, level="INFO", symbol="": lines.append(msg))
    ok = MT5Client.close_position(_client(), TICKET)
    return ok, lines


def test_realised_pnl_comes_from_the_closing_deal(monkeypatch):
    ok, lines = _close(monkeypatch, (_deal(),))
    assert ok is True
    line = next(m for m in lines if "kapatildi" in m)
    # -13.10 + -0.50 + -0.40 = -14.00, not the -12.90 floating figure.
    assert "kar=-14.00" in line
    assert "-12.90" not in line


def test_close_position_puts_realised_pnl_on_the_fill(monkeypatch):
    """Autopsy flatten cash comes from this dict, not a second deal walk."""
    monkeypatch.setattr("micofx.mt5client.mt5", _mt5((_deal(),)))
    monkeypatch.setattr("micofx.mt5client._FILL_RETCODES", frozenset({10009, 10010}))
    fill: dict = {}
    ok = MT5Client.close_position(_client(), TICKET, fill=fill)
    assert ok is True
    assert fill["profit"] == -14.00


def test_fill_profit_uses_the_floating_fallback_when_history_is_empty(monkeypatch):
    monkeypatch.setattr("micofx.mt5client.mt5", _mt5(()))
    monkeypatch.setattr("micofx.mt5client._FILL_RETCODES", frozenset({10009, 10010}))
    fill: dict = {}
    ok = MT5Client.close_position(_client(), TICKET, fill=fill)
    assert ok is True
    assert fill["profit"] == -13.30


def test_partial_fills_of_one_close_are_summed(monkeypatch):
    deals = (_deal(profit=-9.0, commission=-0.3, swap=-0.2),
             _deal(profit=-4.0, commission=-0.2, swap=-0.2))
    _ok, lines = _close(monkeypatch, deals)
    assert "kar=-13.90" in next(m for m in lines if "kapatildi" in m)


def test_a_deal_for_another_position_is_ignored(monkeypatch):
    deals = (_deal(position=999999, profit=1000.0, commission=0.0, swap=0.0),
             _deal())
    _ok, lines = _close(monkeypatch, deals)
    assert "kar=-14.00" in next(m for m in lines if "kapatildi" in m)


@pytest.mark.parametrize("deals", [(), None, RuntimeError("ipc")])
def test_an_unreadable_history_falls_back_and_says_so(monkeypatch, deals):
    # Never silently print the other quantity under the same label.
    ok, lines = _close(monkeypatch, deals)
    assert ok is True
    line = next(m for m in lines if "kapatildi" in m)
    assert "kar~-13.30" in line      # floating -12.90 + swap -0.40
    assert "(anlik)" in line
    assert "kar=" not in line


def test_the_close_still_succeeds_when_the_lookup_explodes(monkeypatch):
    # The lookup runs after the close landed; it must never take it down.
    ok, _lines = _close(monkeypatch, RuntimeError("boom"))
    assert ok is True


def test_a_partial_close_logs_no_full_close_line(monkeypatch):
    monkeypatch.setattr("micofx.mt5client.mt5", _mt5((_deal(),), send_retcode=10010))
    monkeypatch.setattr("micofx.mt5client._FILL_RETCODES", frozenset({10009, 10010}))
    lines: list[str] = []
    monkeypatch.setattr(LOG, "emit",
                        lambda msg, level="INFO", symbol="": lines.append(msg))
    MT5Client.close_position(_client(), TICKET)
    assert any("kismen" in m for m in lines)
    assert not any("kar=" in m for m in lines)
