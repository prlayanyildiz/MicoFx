"""A bar's timestamp may only be compared against the broker's own clock.

``state.next_bar_at`` is built from ``bars.last_closed_time`` - a naive epoch
holding the broker's wall-clock reading. ``server_now()`` is a true epoch, this
machine's. Subtracting one from the other leaves the broker's entire UTC offset
in the answer: +10800 on this GMT+3 server.

Measured 15.08 at 00:01 local: the last closed M5 bar was stamped 164 minutes
"ahead" of local time and ``next_bar_at`` 174 minutes ahead, so
``server_now() >= next_bar_at`` was False on every cycle and had been for the
life of the process. Nothing looked broken, because ``stale`` fires every 45
seconds and refreshed the bars anyway - the intended trigger was dead and a
fallback carried the system silently. It also moved every entry off the bar
close and onto that 45-second timer, which is what the measured 21-30 seconds
into the bar entry timing was.

``market_open`` had the identical bug and its docstring already states the rule:
compare two readings of the same clock, which cancels the offset and needs no
detection. This is that rule applied to the second place that broke it.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.mt5client import MT5Client

SRC = inspect.getsource(Engine._refresh_signals)


def test_the_due_check_reads_the_broker_clock():
    assert "self.client.broker_now()" in SRC, (
        "next_bar_at is broker-stamped; the clock it is compared against must be too")


def test_the_due_check_no_longer_reads_the_local_clock():
    due = SRC[SRC.index("due ="):SRC.index("stale =")]
    assert "server_now()" not in due, (
        "server_now() is a true epoch and leaves the broker's UTC offset in the answer")


def test_an_unread_broker_clock_falls_back_rather_than_firing():
    """0.0 means 'no tick yet', not 'the epoch began'.

    Without the guard, a zero clock makes `0 >= next_bar_at` false anyway, but
    only by accident of sign - and a future refactor that flips the comparison
    would then treat an unknown clock as an infinitely old one and refetch bars
    every cycle for every symbol.
    """
    assert "broker_now > 0.0 and" in SRC


def test_the_client_exposes_the_broker_clock():
    assert hasattr(MT5Client, "broker_now")
    doc = inspect.getdoc(MT5Client.broker_now) or ""
    assert "0.0" in doc, "callers have to be told what an unread clock looks like"


def test_the_broker_clock_starts_unknown_and_tracks_the_newest_reading():
    client = MT5Client.__new__(MT5Client)
    client._broker_now = 0.0
    assert client.broker_now() == 0.0

    client._broker_now = 1786751699.0
    assert client.broker_now() == 1786751699.0


def test_market_open_still_uses_the_same_yardstick():
    """The rule this fix follows is stated there; it must not drift apart."""
    src = inspect.getsource(MT5Client.market_open)
    assert "self._broker_now" in src
