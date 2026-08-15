"""H1 is searchable again, and the refusal machinery still works for real gaps.

H1 left the search on 14.08 for wall-clock, and came back on 15.08 once the cost
was measured rather than assumed: the broker holds about 50k H1 bars per symbol
against 99k at the lower timeframes, so restoring it adds **17.8%** to the bars
a full sweep simulates, not the third that "one more timeframe" suggests.

What bought it back was the book's expensive symbols. Spread as a share of R:
UK100 21.3% at M5 against 8.6% at H1, FRA40 13.1% against 4.4%, SpotBrent 12.3%
against 6.9%. Those three had been moved to M5 by a cost-blind search and UK100
was refusing 95.4% of its own bars at the live cost gate - H1 is the only
timeframe it can afford, and removing it had left nowhere to go.

The tests that asserted "H1 is refused" are inverted here rather than deleted:
the refusal path they covered is real and still needed, so it is now exercised
with a timeframe that genuinely is not searchable.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.mt5client import timeframe_seconds
from micofx.models import READABLE_TIMEFRAMES, TIMEFRAMES

UNSEARCHABLE = "M1"          # measured 14.08: noisier than it is worth


def test_h1_is_offered_again():
    assert "H1" in TIMEFRAMES


def test_h1_still_has_its_own_length():
    assert timeframe_seconds("H1") == 3600


def test_everything_searchable_is_also_readable():
    """A row can outlive its own timeframe leaving the menu; the reverse is a bug."""
    assert set(TIMEFRAMES) <= set(READABLE_TIMEFRAMES)


def test_a_timeframe_that_is_not_searchable_is_still_refused():
    """The refusal path H1 used to exercise - M1 exercises it now."""
    assert UNSEARCHABLE not in TIMEFRAMES


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
