"""M5 was never searched once, and nobody decided that.

``_plan_symbol`` asks for the same calendar window on every timeframe, so a
365-day lookback becomes 45000 M5 bars. A terminal that does not hold that much
M5 history answers with nothing at all rather than with fewer bars, and the
caller files the timeframe as "veri yetersiz (0 bar)" and drops it.

The result is invisible: across the 104 optimisation runs recorded in this
book, **not one** carries an M5 candidate. M15 has 66, M30 27, H1 11. It reads
like M5 was tried and never won. It was never tried.

Measured on 13.08: the same request at 8000 bars returns data and the sweep
runs normally - NAS100 came back with wavetrend_flip at -48.05 net R, GER40
with aroon_flip at +15.94. Whether M5 deserves a place in the book is a
question the search should answer; a data-fetch failure was answering it
instead.

The retry halves until the terminal serves something or the floor is reached.
The floor is 1200, twice the 600-bar minimum the caller already enforces, so
this can never manufacture a sample too thin to judge - it just stops asking
for more history than exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OPTIMIZER_SRC = (Path(__file__).resolve().parents[1] / "micofx" / "optimizer.py").read_text(
    encoding="utf-8")


class _Client:
    """Serves nothing above ``cap`` bars, like a terminal short on history."""

    def __init__(self, cap):
        self.cap = cap
        self.asked = []

    def bars(self, symbol, tf, count):
        self.asked.append(count)
        if count > self.cap:
            return None
        return list(range(count))


def _fetch(client, want):
    """The loop under test, reproduced from _plan_symbol."""
    got = client.bars("X", "M5", want)
    while (got is None or len(got) < 600) and want > 1200:
        want //= 2
        got = client.bars("X", "M5", want)
    return got


# ------------------------------------------------------------- the defect

def test_it_retries_smaller_instead_of_dropping_the_timeframe():
    c = _Client(cap=10000)
    got = _fetch(c, 45000)
    assert got is not None and len(got) >= 600, "zaman dilimi hala dusuyor"
    assert c.asked[0] == 45000, "once tam pencere denenmeli"
    assert len(c.asked) > 1, "hic yeniden denenmemis"


def test_it_keeps_the_longest_window_the_terminal_can_serve():
    """Halving, not jumping straight to the floor."""
    c = _Client(cap=10000)
    _fetch(c, 45000)
    assert c.asked == [45000, 22500, 11250, 5625]
    assert 5625 <= 10000


def test_the_optimizer_carries_this_loop():
    assert "while (got is None or len(got) < 600) and want > 1200:" in OPTIMIZER_SRC
    assert "want //= 2" in OPTIMIZER_SRC


# --------------------------------------------------- what must keep working

def test_a_terminal_with_full_history_is_asked_exactly_once():
    c = _Client(cap=100000)
    got = _fetch(c, 45000)
    assert c.asked == [45000]
    assert len(got) == 45000


def test_a_symbol_with_no_history_at_all_still_gives_up():
    """The caller's own 600-bar check must still be able to reject it."""
    c = _Client(cap=0)
    got = _fetch(c, 45000)
    assert got is None
    assert c.asked[-1] <= 1200, "taban asilmis - sonsuz kucultme"


def test_the_floor_stays_above_the_callers_minimum():
    """1200 is twice the 600 the caller enforces, so a retry can never hand
    back a sample the caller would then have to reject as too thin."""
    assert "len(bars) < 600" in OPTIMIZER_SRC
    assert "want > 1200" in OPTIMIZER_SRC
