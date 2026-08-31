"""The bar-age gate was one whole bar tighter than the comment describes.

``_MAX_SIGNAL_BAR_AGE_BARS`` is documented as "the bar that follows it, plus
one extra bar of poll slack" - two bars of life after the signal bar closes.
The comparison ran against ``state.last_bar``, which is ``bars.last_closed_time``,
the **open** stamp of that bar. One of the two bars was therefore spent on the
signal bar's own duration before the poll loop got a single look at it, so the
real budget was one bar, not two.

Measured live 31.08 01:15 with the old arithmetic: seven of nine symbols sat on
``entry_block = "bar_bosluk"`` at the same moment, NAS100 and US30 showing
``"sinyal bari gecmis (bosluk)"`` outright. Zero symbols were in a state where
a signal could be taken.

The weekend-gap case the constant exists for is untouched: Friday's close to
Monday's open is measured in days, not in one extra M30 bar.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from micofx.engine import _MAX_SIGNAL_BAR_AGE_BARS, signal_bar_expired

M30 = 1800
OPEN = 1_700_000_000  # the signal bar's open stamp
CLOSE = OPEN + M30


# ------------------------------------------------------------- the defect

def test_a_signal_inside_the_second_bar_after_close_still_stands():
    """This is the case the old gate refused. One bar past the close is the
    poll slack the constant's own comment promises."""
    assert signal_bar_expired(OPEN, CLOSE + M30 + 60, M30) is False


def test_the_budget_is_two_bars_measured_from_the_close():
    last_live = CLOSE + _MAX_SIGNAL_BAR_AGE_BARS * M30
    assert signal_bar_expired(OPEN, last_live, M30) is False
    assert signal_bar_expired(OPEN, last_live + 1, M30) is True


# --------------------------------------------------- what must keep working

def test_a_fresh_bar_is_never_expired():
    assert signal_bar_expired(OPEN, CLOSE + 1, M30) is False


def test_the_weekend_gap_is_still_refused():
    """24.08 GER40: Friday 22:30 bar, Monday 03:15 fill, -1R in 12 minutes."""
    friday_to_monday = 52 * 3600
    assert signal_bar_expired(OPEN, OPEN + friday_to_monday, M30) is True


def test_an_unset_last_bar_is_not_an_expiry():
    """last_bar 0 means we have never seen a bar, not that the bar is old."""
    assert signal_bar_expired(0, CLOSE + 10 * M30, M30) is False


@pytest.mark.parametrize("tf_sec", [300, 900, 1800])
def test_the_window_scales_with_the_timeframe(tf_sec):
    close = OPEN + tf_sec
    assert signal_bar_expired(OPEN, close + tf_sec, tf_sec) is False
    assert signal_bar_expired(OPEN, close + 3 * tf_sec, tf_sec) is True
