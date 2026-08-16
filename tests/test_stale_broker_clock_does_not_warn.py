"""A shut market must not be reported as a timezone change.

MetaTrader5's Python API exposes no TimeCurrent(). The only broker clock is
the newest tick stamp, so over a weekend it stands still and the difference
against this machine's clock stops being an offset and becomes "hours since
the close". The first version of the check read that difference as a skew and
spent Sunday logging "broker saati yerel saatten -42 saat farkli", which is
both false and loud enough to bury the real one-hour drift in October.
"""
from __future__ import annotations

import time

from micofx import sessions
from micofx.engine import BROKER_CLOCK_MAX_AGE_SEC, Engine


class _Clock:
    """Enough of MT5Client for the clock check: a stamp and its age."""

    def __init__(self, broker_now: float, age: float | None) -> None:
        self._broker_now = broker_now
        self._age = age

    def broker_now(self) -> float:
        return self._broker_now

    def broker_now_age(self) -> float | None:
        return self._age

    def server_now(self) -> float:
        return time.time()


def _skew(broker_offset_h: float, age: float | None) -> int | None:
    """Skew the engine reports when the broker sits at ``broker_offset_h`` UTC.

    A naive broker stamp is ``true_utc + broker_offset``, so that is what the
    fake client hands back; ``age`` is how long since it last moved.
    """
    now = time.time()
    eng = Engine.__new__(Engine)
    eng.client = _Clock(now + broker_offset_h * 3600.0, age)
    return eng._measured_clock_skew(now)


def test_weekend_stamp_is_not_a_skew():
    """Friday's close read on Sunday is 40 hours old, not 40 hours shifted."""
    assert _skew(broker_offset_h=-40.0, age=40 * 3600.0) is None


def test_no_reading_yet_is_not_a_skew():
    assert _skew(broker_offset_h=3.0, age=None) is None


def test_fresh_matching_clocks_report_zero():
    local_h = sessions.local_utc_offset_seconds(time.time()) / 3600.0
    assert _skew(broker_offset_h=local_h, age=5.0) == 0


def test_fresh_one_hour_drift_is_reported():
    """The October case: broker drops to UTC+2 while Windows stays UTC+3."""
    local_h = sessions.local_utc_offset_seconds(time.time()) / 3600.0
    assert _skew(broker_offset_h=local_h - 1.0, age=5.0) == -1


def test_bound_rejects_an_impossible_gap():
    """No two wall clocks sit 42 hours apart; that reading is stale, not shifted."""
    assert sessions.session_clock_skew_hours(time.time() - 42 * 3600.0) is None
    assert sessions.MAX_CLOCK_SKEW_HOURS < 42


def test_age_bound_is_hours_not_minutes():
    """Ticks thin out overnight; the case being caught is a closed market."""
    assert BROKER_CLOCK_MAX_AGE_SEC >= 300.0
