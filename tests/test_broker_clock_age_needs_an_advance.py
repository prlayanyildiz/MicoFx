"""A broker clock that is readable is not the same as one that is running.

MetaTrader5 exposes no TimeCurrent, so the newest tick stamp is the only
broker clock there is, and it stands still while the market is shut. The
staleness guard that keeps a frozen stamp out of the decision path measured
how long THIS PROCESS had been watching, which a restart resets - so on 22.08
a bot restarted on a Saturday reported the skew as minus eight hours and,
underneath the warning, handed Friday's close to the last-mile weekend check
as a current broker time. Asked about a Friday, it said it was not the
weekend.

Requiring an advance was tried and measured insufficient: the book's six
symbols froze at slightly different seconds, so reading them in turn produces
real advances from real values while nothing moves. A process carrying that
guard still logged the warning twenty seconds after starting.

What separates a running clock from a frozen one is pace. Over a window, a
running clock gains broker seconds at roughly the rate local seconds pass; a
frozen one gains the spread between symbol stamps and then nothing.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.mt5client import BROKER_CLOCK_MIN_WINDOW_SEC, MT5Client


def _client() -> MT5Client:
    c = object.__new__(MT5Client)
    c._broker_now = 0.0
    c._broker_seen_at = 0.0
    c._broker_last_advance_at = 0.0
    c._broker_anchor = None
    return c


def _observe(c: MT5Client, stamp: float, at: float | None = None) -> None:
    """The clock bookkeeping from tick(), without a terminal."""
    now = time.time() if at is None else at
    if stamp > c._broker_now:
        if c._broker_anchor is None:
            c._broker_anchor = (now, stamp)
        c._broker_now = stamp
        c._broker_seen_at = now
        c._broker_last_advance_at = now


def test_age_is_unknown_before_any_tick():
    assert _client().broker_now_age() is None


def test_the_window_is_not_answered_before_it_is_long_enough():
    """For the first ~30s after a restart the answer is "unknown", by design."""
    c = _client()
    _observe(c, time.time())
    assert c.broker_now_age() is None
    assert c.decision_now() is None


def test_stamps_frozen_at_different_seconds_do_not_read_as_a_running_clock():
    """The measured failure: six symbols, six slightly different frozen stamps."""
    c = _client()
    started = time.time() - (BROKER_CLOCK_MIN_WINDOW_SEC + 30)
    friday = started - 8 * 3600
    # Seeding across the book: real advances, spread over four seconds.
    for i, offset in enumerate((0.0, 1.0, 2.0, 2.5, 3.0, 4.0)):
        _observe(c, friday + offset, at=started + i * 0.4)

    assert c.broker_now_age() is None, "donmus kitap kosan saat sayilmamali"
    assert c.decision_now() is None, "bayat damga karar saati olarak verilmemeli"


def test_a_clock_keeping_pace_with_local_time_is_accepted():
    c = _client()
    started = time.time() - (BROKER_CLOCK_MIN_WINDOW_SEC + 30)
    broker0 = started - 3 * 3600          # a real offset, constant throughout
    for k in range(0, 91, 10):            # 90 seconds of local time, matched
        _observe(c, broker0 + k, at=started + k)

    age = c.broker_now_age()
    assert age is not None, "kosan saat olculebilmeli"
    assert c.decision_now() is not None


def test_slow_feed_partial_pace_is_accepted_when_stamps_keep_moving():
    """Index ticks can advance slower than 0.2x local; recent moves still count."""
    c = _client()
    started = time.time() - (BROKER_CLOCK_MIN_WINDOW_SEC + 10)
    broker0 = started - 3 * 3600
    for k in (0, 15, 30, 35):
        _observe(c, broker0 + k * 0.1, at=started + k)
    assert c.decision_now() is not None


def test_a_clock_that_freezes_mid_run_stops_being_measurable():
    """Pace decays, and the last-advance age closes the gate before it does."""
    c = _client()
    started = time.time() - 4 * 3600
    broker0 = started - 3 * 3600
    for k in range(0, 3601, 300):         # an hour of healthy tracking
        _observe(c, broker0 + k, at=started + k)
    # Then the market shuts: three more hours of local time, no new stamps.
    assert c.decision_now() is None, "donunca karar saati kapanmali"
