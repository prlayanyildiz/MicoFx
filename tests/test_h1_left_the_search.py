"""H1 left the search for good, and the refusal machinery still works.

Three moves in two days, and only the last two were measurements. It left 14.08
on a wall-clock guess. It came back 15.08 on a real cost reading: the broker
holds ~50k H1 bars per symbol against 99k lower down, so restoring it added
17.8% to a full sweep rather than the third that "one more timeframe" suggests,
and spread as a share of R was 8.6% at H1 against 21.3% at M5 for UK100, 4.4%
against 13.1% for FRA40, 6.9% against 12.3% for SpotBrent. UK100 was refusing
95.4% of its own bars at the live cost gate and H1 was the only bar it could
afford.

It left again the same evening on the reading that outranks cost: **0.110 R per
day against M5's 1.303**. Per trade the hourly bar is the cheaper one; per day
it is nowhere near, because it takes a twelfth of the trades to get there. At
this account size the day is the unit that compounds, so the expensive symbols
were moved instead - nothing in the book is hourly, and the cost argument that
bought H1 back has no symbol left to speak for.

Both TIMEFRAMES and READABLE_TIMEFRAMES drop it: they only needed to differ
while a live row still named H1, and none does. Reopening it takes one line and
needs a R/day number, not a spread number.

The tests that asserted "H1 is offered" are inverted here rather than deleted:
the refusal path is real and still needed, and M1 exercises the other half.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import READABLE_TIMEFRAMES, TIMEFRAMES
from micofx.mt5client import timeframe_seconds

UNSEARCHABLE = "M1"          # measured 14.08: noisier than it is worth


def test_h1_is_not_offered():
    assert "H1" not in TIMEFRAMES
    assert "H1" not in READABLE_TIMEFRAMES, (
        "readable only had to outlive searchable while a live row named H1")


def test_h1_no_longer_translates_to_its_own_length():
    """It falls to M5 like any other unknown name - loudly, per mt5client."""
    assert timeframe_seconds("H1") == 300


def test_everything_searchable_is_also_readable():
    """A row can outlive its own timeframe leaving the menu; the reverse is a bug."""
    assert set(TIMEFRAMES) <= set(READABLE_TIMEFRAMES)


def test_a_timeframe_that_is_not_searchable_is_still_refused():
    """M1 and H1 both exercise it now, for different reasons."""
    assert UNSEARCHABLE not in TIMEFRAMES
    assert "H1" not in TIMEFRAMES


def test_an_unsearchable_only_request_is_refused_in_the_source():
    """Falling back to every timeframe would silently search the wrong thing.

    Asserted on the branch rather than by driving start(), which needs a live
    store, client and thread - the behaviour itself is covered where those
    exist; this pins that the branch has not been deleted.
    """
    import inspect

    from micofx.optimizer import Optimizer

    src = inspect.getsource(Optimizer.start)
    assert "Aranabilir zaman dilimi yok" in src, (
        "a request naming only unsearchable bars must refuse, not fall back")
    assert "Aranamayan zaman dilimi istekten dusuruldu" in src


def test_a_historical_row_on_any_readable_timeframe_still_resolves():
    """opt_runs keeps rows from timeframes that have come and gone."""
    for name in READABLE_TIMEFRAMES:
        assert timeframe_seconds(name) > 0
