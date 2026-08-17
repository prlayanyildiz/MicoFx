"""Pepperstone TRADE_ACTION_DEAL success is retcode=0 comment=Done.

OPS-2 already accepted that shape on TRADE_ACTION_SLTP. The DEAL path
still treated it as a plain reject (``emir reddedildi (0 Done)``), so the
engine never armed cooldown or the filled-bar lock and the next poll
sent a second order on top of a fill that already existed.

Live 17.08.2026 GER40 (server clock): fill #359585333 then, two seconds
later, fill #359585371. Same bar, cooldown_sec=120 never written.

None is still a failure. retcode=0 with an empty comment is still a
failure. 10009/10010 stay success so a broker that speaks the documented
codes is unchanged.
"""
from __future__ import annotations

import threading
import types

from micofx.mt5client import AMBIGUOUS_RETCODES, NON_RETRYABLE_RETCODES, MT5Client


class _Pos:
    def __init__(self, ticket, magic, price_open=1.1000, volume=0.10, sl=1.0950, tp=1.1050):
        self.ticket = ticket
        self.magic = magic
        self.price_open = price_open
        self.volume = volume
        self.sl = sl
        self.tp = tp


class _Deal:
    def __init__(self, ticket=1, position_id=4321):
        self.ticket = ticket
        self.position_id = position_id


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


def _mt5_stub(send, *, positions=(), deals=()):
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
        ORDER_FILLING_IOC = 1
        ORDER_FILLING_FOK = 2
        ORDER_FILLING_RETURN = 3

        @staticmethod
        def positions_get(**kwargs):
            return positions

        @staticmethod
        def history_deals_get(**kwargs):
            return deals

        @staticmethod
        def order_send(request):
            return send(request)

        @staticmethod
        def last_error():
            return (1, "Success")

    return _MT5


def _install(monkeypatch, mt5_cls):
    monkeypatch.setattr("micofx.mt5client.mt5", mt5_cls)
    monkeypatch.setattr(
        "micofx.mt5client._FILL_RETCODES",
        frozenset({mt5_cls.TRADE_RETCODE_DONE, mt5_cls.TRADE_RETCODE_DONE_PARTIAL}),
    )


def _done_zero(**extra):
    fields = {"retcode": 0, "comment": "Done", "price": 1.1000, "order": 99, "deal": 1,
              "volume": 0.10}
    fields.update(extra)
    return types.SimpleNamespace(**fields)


def test_pepperstone_done_zero_is_an_open_market_fill(monkeypatch):
    """Today this returns ok=False with 'emir reddedildi (0 Done)'."""
    client = _make_client()
    mt5_cls = _mt5_stub(lambda request: _done_zero(), deals=(_Deal(),))
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is True
    assert out["position"] == 4321
    assert out["price"] == 1.1000
    assert out["volume"] == 0.10
    assert out["partial_fill"] is False


def test_open_market_none_is_still_not_success(monkeypatch):
    client = _make_client()
    mt5_cls = _mt5_stub(lambda request: None, positions=())
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is False


def test_open_market_bare_zero_without_done_is_still_a_reject(monkeypatch):
    client = _make_client()
    result = types.SimpleNamespace(retcode=0, comment="", price=0.0, order=0,
                                   deal=0, volume=0.0)
    mt5_cls = _mt5_stub(lambda request: result)
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is False
    assert out.get("retcode") == 0
    assert "reddedildi" in out["error"]
    assert not out.get("verified_unfilled")
    assert not out.get("ambiguous")


def test_zero_is_not_an_ambiguous_or_non_retryable_code():
    """A false reject of 0/Done is treated as a plain emir_hatasi.

    AMBIGUOUS_RETCODES does not include 0, so the engine will not drop the
    signal and will not park the symbol. The next poll retries. That is the
    duplicate-position path; the fix is counting 0/Done as success, not
    widening the ambiguous set.
    """
    assert 0 not in AMBIGUOUS_RETCODES
    assert 0 not in NON_RETRYABLE_RETCODES


def test_invalid_fill_ladder_accepts_pepperstone_done(monkeypatch):
    sends = {"n": 0}

    def order_send(request):
        sends["n"] += 1
        if sends["n"] == 1:
            return types.SimpleNamespace(retcode=10030, comment="Invalid filling",
                                         price=0.0, order=0, deal=0, volume=0.0)
        return _done_zero()

    client = _make_client()
    mt5_cls = _mt5_stub(order_send, deals=(_Deal(),))
    _install(monkeypatch, mt5_cls)

    out = MT5Client.open_market(client, "EURUSD", "buy", 0.10, 1.0950, 1.1050, magic=7)

    assert out["ok"] is True
    assert sends["n"] >= 2
    assert out["position"] == 4321


def test_close_position_pepperstone_done_zero_is_success(monkeypatch):
    class _ClosePos:
        ticket = 4242
        symbol = "GER40"
        magic = 7
        volume = 0.3
        type = 0
        price_open = 26482.2
        sl = 26462.2
        tp = 0.0
        profit = -19.99
        swap = 0.0

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
            return (_ClosePos(),)

        @staticmethod
        def order_send(request):
            return types.SimpleNamespace(retcode=0, comment="Done", price=26462.2,
                                         order=777, deal=99, volume=0.3)

        @staticmethod
        def history_deals_get(**kwargs):
            return ()

        @staticmethod
        def last_error():
            return (1, "Success")

    monkeypatch.setattr("micofx.mt5client.mt5", _MT5)
    monkeypatch.setattr("micofx.mt5client._FILL_RETCODES", frozenset({10009, 10010}))
    client = object.__new__(MT5Client)
    client.connected = True
    client._lock = threading.Lock()
    client.tick = lambda symbol: {"bid": 26462.0, "ask": 26462.2}
    client._filling = lambda symbol: 1

    assert MT5Client.close_position(client, 4242) is True


def test_deal_and_sltp_share_one_success_helper():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "micofx" / "mt5client.py").read_text(
        encoding="utf-8")
    assert "def _broker_send_succeeded(" in src
    # The helper may consult _FILL_RETCODES. DEAL/close success gates must not.
    assert "result.retcode in _FILL_RETCODES" not in src
    assert "result.retcode not in _FILL_RETCODES" not in src
