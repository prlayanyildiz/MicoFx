"""One tick dated into the future must not stop the whole book trading.

``_broker_now`` is a monotonic max over every tick timestamp the client has
ever seen. It starts at 0.0, is only ever raised, and is never reset - not by
connect(), not by reconnect(), not by shutdown(). market_open() measures each
symbol's freshness against it, deliberately, so that two readings of the same
broker clock cancel the UTC offset out.

The cost of that design is that the yardstick is shared. A single corrupt
timestamp - a milliseconds field read into a seconds one, a garbled struct,
a feed glitch on any one instrument - raises it permanently, and from then on
every symbol in the book is measured against a clock that is years ahead of
the feed. Instruments quoting perfectly fresh ticks all read as stale.

engine._evaluate turns market_open() == False into "piyasa kapali / fiyat
akmiyor" and clears the signal chain, for every symbol. So the bot stops
taking entries entirely, permanently, and reports it as a market condition
rather than a fault. Open positions stay managed - manage_positions() never
consults this gate - so the failure is silent rather than dangerous, which is
what makes it hard to notice.

The tick() guard is one-sided by design: a timestamp in the PAST is exactly
what market_open() exists to catch and must always be kept.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import mt5client as mod
from micofx.mt5client import MT5Client

HOUR = 3600.0


class _Tick:
    def __init__(self, t: float, bid: float = 1.0, ask: float = 1.1) -> None:
        self.time, self.bid, self.ask = t, bid, ask


def _client() -> MT5Client:
    c = object.__new__(MT5Client)
    c._lock = threading.Lock()
    c._tick_cache = {}
    c._info_cache = {}
    c._broker_now = 0.0
    c._broker_seen_at = 0.0
    c._broker_anchor = None
    c.select = lambda s: s
    return c


@pytest.fixture
def feed(monkeypatch):
    book: dict[str, _Tick] = {}

    class _M:
        @staticmethod
        def symbol_info_tick(name):
            return book.get(name)

    monkeypatch.setattr(mod, "mt5", _M())
    return book


def _read(c, symbol):
    """market_open() with the 0.5s tick cache stepped over."""
    c._tick_cache.clear()
    return MT5Client.market_open(c, symbol)


# --------------------------------------------------------------- the bug

@pytest.mark.parametrize("ahead", [
    10 * 365 * 86400,        # a decade out
    49 * HOUR,               # just past the bound
    1e6 * 86400,             # a milliseconds field read as seconds
])
def test_a_future_tick_does_not_freeze_every_other_symbol(feed, ahead):
    now = time.time()
    c = _client()
    feed["A"] = _Tick(now)
    feed["B"] = _Tick(now)
    assert _read(c, "A") is True

    feed["B"] = _Tick(now + ahead)
    _read(c, "B")

    # A is untouched and still quoting - it must still be open.
    feed["B"] = _Tick(now)
    assert _read(c, "A") is True, "tek bozuk tick tum kitabi kilitledi"
    assert _read(c, "B") is True


def test_the_corrupt_tick_itself_is_refused(feed):
    now = time.time()
    c = _client()
    feed["A"] = _Tick(now + 10 * 365 * 86400)
    assert MT5Client.tick(c, "A") is None
    assert MT5Client.market_open(c, "A") is False


def test_the_shared_clock_is_never_raised_by_it(feed):
    now = time.time()
    c = _client()
    feed["A"] = _Tick(now)
    MT5Client.tick(c, "A")
    good = c._broker_now

    feed["B"] = _Tick(now + 10 * 365 * 86400)
    c._tick_cache.clear()
    MT5Client.tick(c, "B")
    assert c._broker_now == good


# ------------------------------------------- what must keep working

@pytest.mark.parametrize("offset", [0.0, 3 * HOUR, 14 * HOUR, -12 * HOUR])
def test_every_real_broker_offset_still_passes(feed, offset):
    """tick.time carries the broker's whole UTC offset; +14h is the world max."""
    now = time.time()
    c = _client()
    feed["A"] = _Tick(now + offset)
    assert MT5Client.tick(c, "A") is not None
    assert _read(c, "A") is True


def test_a_stale_tick_is_still_caught(feed):
    """The past side must stay untouched - it is the whole point of the gate."""
    now = time.time()
    c = _client()
    feed["A"] = _Tick(now)
    feed["B"] = _Tick(now - 3600)
    _read(c, "A")
    assert _read(c, "B") is False


def test_a_bad_quote_is_still_refused(feed):
    """The guard this one sits beside."""
    now = time.time()
    c = _client()
    for bid, ask in ((0.0, 1.1), (1.0, 0.0), (0.0, 0.0), (-1.0, 1.1)):
        feed["A"] = _Tick(now, bid, ask)
        c._tick_cache.clear()
        assert MT5Client.tick(c, "A") is None, f"{bid}/{ask} gecti"
