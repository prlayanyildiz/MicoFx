"""Broker wall clock leaving the machine's must be visible, not silent.

Pepperstone follows European DST and drops to UTC+2 at the end of October;
Turkey stays UTC+3. Session windows are configured against Windows local
time; backtest reads naive broker bar stamps. The two clocks agree today
by accident. When they split, nothing in the code said so.

Found by comparing sessions.server_clock(time.time()) against the backtest
epoch reading of the same number: 3 hours apart, each correct for its own
input. Measurement only - no session rewrite.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.sessions import session_clock_skew_hours, session_clock_warning

HOUR = 3600
# Arbitrary true epoch. Offset is injected so the test is not the machine TZ.
LOCAL = 1_700_000_000.0
TR = 3 * HOUR


def test_aligned_clocks_do_not_warn():
    # Broker wall encoded as UTC sits +3h ahead of a true epoch on GMT+3.
    broker = LOCAL + TR
    assert session_clock_skew_hours(broker, LOCAL, local_utc_offset_sec=TR) == 0
    assert session_clock_warning(0) is None


def test_a_one_hour_split_warns():
    """October: broker UTC+2, Windows still UTC+3."""
    broker = LOCAL + 2 * HOUR
    skew = session_clock_skew_hours(broker, LOCAL, local_utc_offset_sec=TR)
    assert skew == -1
    warn = session_clock_warning(skew)
    assert warn is not None
    assert "1 saat" in warn
    assert "backtest" in warn


def test_unknown_broker_now_is_not_a_false_alarm():
    assert session_clock_skew_hours(0.0, LOCAL, local_utc_offset_sec=TR) is None
    assert session_clock_warning(None) is None
