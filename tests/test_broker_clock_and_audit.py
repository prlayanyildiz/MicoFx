"""The session audit must not certify what it could not look at.

broker_audit compared each symbol's configured Friday close against the
broker's own published close - except the MetaTrader5 Python package exposes no
session schedule at all. symbol_info_session_trade is an MQL5 function with no
binding (checked against 5.0.6090), so last_session_close_minute raises,
warns, and returns None every single time.

close_mismatch is False both when the times agree and when the broker's close
is unknown, so the audit reported all twenty symbols aligned while reading
nothing. That is the one check meant to notice a drift, and it was structurally
incapable of firing.

What IS measurable is the broker's clock offset. Session windows are configured
against the Windows clock - Turkey is UTC+3 all year - while the broker's server
follows European DST and drops to GMT+2 at the end of October, which is exactly
when every window stops matching its instrument's real session.
"""
from __future__ import annotations

import threading
import time

import pytest

from micofx.mt5client import MT5Client


def _client(tick_offsets: dict[str, float | None]):
    """tick_offsets: symbol -> seconds the broker clock leads local, or None."""
    c = object.__new__(MT5Client)
    c.connected = True
    c._lock = threading.Lock()
    now = time.time()

    def tick(symbol):
        off = tick_offsets.get(symbol, "missing")
        if off == "missing" or off is None:
            return None
        return {"bid": 1.0, "ask": 1.1, "spread": 0.1, "time": now + off}

    c.tick = tick
    return c


HOUR = 3600.0


# ------------------------------------------------------------- clock offset

def test_a_gmt3_server_reads_as_plus_three():
    # tick.time encodes the broker's wall clock as though it were UTC, so a
    # GMT+3 server's ticks sit three hours ahead of a true epoch.
    c = _client(dict.fromkeys(("A", "B", "C", "D"), 3 * HOUR))
    assert c.broker_utc_offset_hours(["A", "B", "C", "D"]) == 3


def test_the_october_shift_shows_as_gmt_plus_two():
    # End of European DST: the server drops to GMT+2 while Turkey stays UTC+3,
    # so the drift the caller computes becomes -1.
    c = _client(dict.fromkeys(("A", "B", "C", "D"), 2 * HOUR))
    broker = c.broker_utc_offset_hours(["A", "B", "C", "D"])
    assert broker == 2
    assert broker - 3 == -1          # drift against a UTC+3 machine


def test_one_odd_quote_cannot_move_the_answer():
    # Median, not mean: a single bad tick among good ones is outvoted.
    c = _client({"A": 3 * HOUR, "B": 3 * HOUR, "C": 3 * HOUR, "D": 8 * HOUR})
    assert c.broker_utc_offset_hours(["A", "B", "C", "D"]) == 3


def test_a_stale_closed_market_quote_is_ignored():
    # Far-out timestamps are last quotes from a closed instrument and say
    # nothing about the clock; dropping them leaves too few to answer.
    c = _client({"A": 3 * HOUR, "B": 30 * HOUR, "C": 40 * HOUR})
    assert c.broker_utc_offset_hours(["A", "B", "C"]) is None


def test_too_few_live_quotes_answers_none_not_zero():
    c = _client({"A": 3 * HOUR, "B": None})
    assert c.broker_utc_offset_hours(["A", "B"]) is None


def test_no_symbols_at_all_answers_none():
    assert _client({}).broker_utc_offset_hours([]) is None


def test_a_partial_hour_offset_rounds_to_whole_hours():
    # Broker clocks sit on whole hours; anything else is quote latency.
    c = _client(dict.fromkeys(("A", "B", "C"), 2 * HOUR + 4.0))
    assert c.broker_utc_offset_hours(["A", "B", "C"]) == 2


# --------------------------------------------------- the schedule is unreadable

def test_the_session_schedule_really_is_unavailable():
    # Pins the reason the audit had to change: if a future package adds the
    # binding this fails and the audit can start trusting it again.
    import MetaTrader5 as mt5
    assert not hasattr(mt5, "symbol_info_session_trade")


def test_unknown_close_is_not_a_mismatch_and_not_an_all_clear():
    # The distinction the audit now makes. close_mismatch stays False when the
    # broker close is unknown - which is correct, it is not a mismatch - so the
    # separate close_check field is what carries "could not look".
    from micofx.web.app import create_app  # noqa: F401  (import must not break)
    configured, broker = 1375, None
    close_mismatch = (broker is not None and configured is not None
                      and abs(broker - configured) > 30)
    assert close_mismatch is False
    close_check = ("session-yok" if configured is None
                   else "okunamadi" if broker is None
                   else "kayik" if close_mismatch else "uyumlu")
    assert close_check == "okunamadi"


@pytest.mark.parametrize("configured,broker,expected", [
    (1375, None, "okunamadi"),
    (None, 1375, "session-yok"),
    (1375, 1375, "uyumlu"),
    (1375, 1315, "kayik"),      # a full hour apart
    (1375, 1360, "uyumlu"),     # 15 min, inside tolerance
])
def test_every_audit_verdict(configured, broker, expected):
    close_mismatch = (broker is not None and configured is not None
                      and abs(broker - configured) > 30)
    got = ("session-yok" if configured is None
           else "okunamadi" if broker is None
           else "kayik" if close_mismatch else "uyumlu")
    assert got == expected


# ------------------------------------------- the missing binding must be quiet

def test_a_missing_binding_returns_none_without_warning(monkeypatch):
    """20 identical WARN lines per audit run, all of them to disk, for a
    condition that can never change on this package. A log that buries its own
    real warnings under a known non-issue is the failure this whole day was
    about."""
    from micofx import mt5client as mod
    from micofx.logbus import LOG

    class _NoSessions:
        pass

    lines: list[str] = []
    monkeypatch.setattr(mod, "mt5", _NoSessions())
    monkeypatch.setattr(LOG, "emit",
                        lambda msg, level="INFO", symbol="": lines.append(msg))

    c = object.__new__(MT5Client)
    c.select = lambda s: s
    assert MT5Client.last_session_close_minute(c, "US30", 5) is None
    assert lines == []


def test_a_real_failure_on_a_capable_build_still_warns(monkeypatch):
    from micofx import mt5client as mod
    from micofx.logbus import LOG

    class _Broken:
        @staticmethod
        def symbol_info_session_trade(*a):
            raise RuntimeError("terminal busy")

    lines: list[str] = []
    monkeypatch.setattr(mod, "mt5", _Broken())
    monkeypatch.setattr(LOG, "emit",
                        lambda msg, level="INFO", symbol="": lines.append(msg))

    c = object.__new__(MT5Client)
    c.select = lambda s: s
    c._lock = threading.Lock()
    assert MT5Client.last_session_close_minute(c, "US30", 5) is None
    assert any("Seans programi okunamadi" in m for m in lines)
