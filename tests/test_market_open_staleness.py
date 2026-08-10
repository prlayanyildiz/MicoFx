"""The dead-feed gate must measure against the feed, not the wall clock.

market_open compared a tick's timestamp against server_now(). A tick's ``time``
is a naive epoch holding the broker's wall-clock reading; server_now() is a
true epoch. Subtracting one from the other leaves the broker's whole UTC offset
in the answer - a constant -10800 on this GMT+3 server - so every tick up to
three hours stale satisfied a 180 second freshness test.

That is the one gate stopping entries on a frozen or dead feed, and it was 61x
more permissive than it reads:

    tick 181s stale  -> -10619 <= 180  -> "open"   (should be closed)
    tick 1h  stale   ->  -7200 <= 180  -> "open"   (should be closed)
    tick 3h  stale   ->     -1 <= 180  -> "open"   (should be closed)

Comparing two readings of the same clock cancels the offset and needs no
detection - which matters, because an auto-detected offset was removed from
this codebase for silently shifting every time-based decision when it went
wrong.
"""
from __future__ import annotations

import threading
import time

import pytest

from micofx.mt5client import MT5Client

# Broker runs GMT+3, so its naive tick epochs sit 3 hours ahead of a true one.
BROKER_UTC_OFFSET = 3 * 3600


def _client(ticks: dict[str, float]):
    """ticks: symbol -> how many seconds stale that symbol's last tick is."""
    c = object.__new__(MT5Client)
    c.connected = True
    c._lock = threading.Lock()
    c._tick_cache = {}
    c._broker_now = 0.0
    broker_now = time.time() + BROKER_UTC_OFFSET

    def tick(symbol):
        stale = ticks.get(symbol)
        if stale is None:
            return None
        data = {"bid": 1.0, "ask": 1.1, "spread": 0.1, "time": broker_now - stale}
        c._broker_now = max(c._broker_now, data["time"])
        return data

    c.tick = tick
    return c


def _warm(c, symbols):
    """Read every symbol once, the way a cycle does, so _broker_now is set."""
    for s in symbols:
        c.tick(s)


@pytest.mark.parametrize("stale,expected", [
    (0, True),
    (60, True),
    (179, True),
    (181, False),      # each of these read as open before
    (600, False),
    (3600, False),
    (10799, False),
])
def test_staleness_is_judged_in_seconds_not_hours(stale, expected):
    c = _client({"LIVE": 0.0, "OTHER": 1.0, "SUT": float(stale)})
    _warm(c, ["LIVE", "OTHER", "SUT"])
    assert c.market_open("SUT") is expected


def test_a_frozen_symbol_is_caught_while_the_book_moves():
    # The real shape of the failure: one instrument's feed stops while the
    # rest keep ticking.
    c = _client({"A": 0.0, "B": 0.0, "FROZEN": 900.0})
    _warm(c, ["A", "B", "FROZEN"])
    assert c.market_open("A") is True
    assert c.market_open("FROZEN") is False


def test_a_single_symbol_still_reads_open():
    # Degrades to the old answer rather than closing a live market: with
    # nothing newer to compare against, its own tick is the newest.
    c = _client({"ONLY": 0.0})
    assert c.market_open("ONLY") is True


def test_no_tick_at_all_is_closed():
    c = _client({"A": 0.0})
    _warm(c, ["A"])
    assert c.market_open("MISSING") is False


def test_the_wall_clock_offset_no_longer_reaches_the_answer():
    # Pins the actual defect. Under the old comparison this tick sat at
    # -10800 + 3600 = -7200, comfortably under 180, and passed.
    c = _client({"LIVE": 0.0, "OTHER": 0.0, "HOUR_OLD": 3600.0})
    _warm(c, ["LIVE", "OTHER", "HOUR_OLD"])
    old_style = time.time() - c.tick("HOUR_OLD")["time"]
    assert old_style <= 180          # the bug, still true of the old formula
    assert c.market_open("HOUR_OLD") is False


def test_a_custom_window_is_honoured():
    c = _client({"LIVE": 0.0, "OTHER": 0.0, "SUT": 500.0})
    _warm(c, ["LIVE", "OTHER", "SUT"])
    assert c.market_open("SUT", max_age_sec=600) is True
    assert c.market_open("SUT", max_age_sec=300) is False
