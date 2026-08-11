"""``adverse_ratio`` must stay a ratio when no fill ever came out in our favour.

The constant it is compared against says what it means: "adverse fills more
than this multiple of favourable ones - points at routing, not at strategy."
With ``favourable == 0`` there is no multiple to take, and the fallback handed
back ``len(adverse)`` instead - a count, wearing a ratio's name and measured
against a ratio's threshold of 3.0.

That inverts the verdict on exactly the venue it was written to praise. A fill
that lands on the requested price is neither adverse nor favourable, so a
symbol filling 96 out of 100 orders perfectly and 4 slightly against us scores
``4.0`` and is reported as "kayma tek yonlu: aleyhte/lehte 4.0x" - a routing
complaint aimed at near-flawless execution. The count also grows with the
window, so the same venue looks worse the longer it behaves.

Reachable: exact fills are the norm on several live symbols (GBPUSD 6/6,
USDCHF 3/3, NZDUSD 2/2 at the time of writing), and MIN_SAMPLES_FOR_SYMMETRY
is 100 against a MAX_SAMPLES window of 400.

The verdict only reaches a WARN line and the panel's flagged list; no sizing or
gate reads it. The cost is a misleading warning, not a mis-sized trade.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.execution import (
    MAX_ADVERSE_RATIO,
    MIN_SAMPLES_FOR_SYMMETRY,
    ExecutionMonitor,
)

_summarise = ExecutionMonitor._summarise
_verdict = ExecutionMonitor._verdict


def _rows(adverse: int = 0, favourable: int = 0, exact: int = 0,
          leg: str = "entry") -> list[dict]:
    """Sample rows carrying only what _summarise reads."""
    return (
        [{"adverse": 0.5, "leg": leg, "points": 1.0} for _ in range(adverse)]
        + [{"adverse": -0.5, "leg": leg, "points": -1.0} for _ in range(favourable)]
        + [{"adverse": 0.0, "leg": leg, "points": 0.0} for _ in range(exact)]
    )


# --------------------------------------------------- the defect, at live sizes

def test_a_venue_that_fills_almost_everything_perfectly_is_not_called_one_sided():
    n = MIN_SAMPLES_FOR_SYMMETRY
    summary = _summarise(_rows(adverse=4, favourable=0, exact=n - 4))
    assert summary["samples"] == n
    assert not _verdict(summary), (
        "96/100 tam dolum 'kayma tek yonlu' diye isaretlendi: "
        f"oran={summary['adverse_ratio']}"
    )


@pytest.mark.parametrize("adverse", [4, 10, 40, 60])   # not 50: 50/50 == 1.0 by
                                                       # ratio too, no signal
def test_the_reported_number_never_just_counts_the_adverse_fills(adverse):
    """The tell: with no favourable fills the value used to equal the count."""
    n = MIN_SAMPLES_FOR_SYMMETRY
    summary = _summarise(_rows(adverse=adverse, favourable=0, exact=n - adverse))
    assert summary["adverse_ratio"] != float(adverse) or adverse == 0


def test_a_longer_window_does_not_make_the_same_venue_look_worse():
    """Same 4% adverse share, twice the samples - the read must not double."""
    short = _summarise(_rows(adverse=4, favourable=0, exact=96))
    long = _summarise(_rows(adverse=8, favourable=0, exact=192))
    assert short["adverse_ratio"] == pytest.approx(long["adverse_ratio"])


# ------------------------------------- genuinely one-sided must still be caught

def test_a_venue_that_only_ever_fills_against_us_is_still_flagged():
    summary = _summarise(_rows(adverse=MIN_SAMPLES_FOR_SYMMETRY, favourable=0))
    assert _verdict(summary), "her dolumu aleyhte olan venue kacti"


def test_mostly_adverse_with_no_favourable_is_still_flagged():
    summary = _summarise(_rows(adverse=90, favourable=0, exact=10))
    assert _verdict(summary)


def test_a_real_lopsided_ratio_is_unchanged():
    summary = _summarise(_rows(adverse=80, favourable=10, exact=10))
    assert summary["adverse_ratio"] == pytest.approx(8.0)
    assert _verdict(summary)


def test_parity_is_never_flagged():
    summary = _summarise(_rows(adverse=50, favourable=50))
    assert summary["adverse_ratio"] == pytest.approx(1.0)
    assert not _verdict(summary)


def test_just_under_the_threshold_is_not_flagged():
    summary = _summarise(_rows(adverse=75, favourable=25))
    assert summary["adverse_ratio"] == pytest.approx(3.0)
    assert not _verdict(summary), "esik > karsilastirmasi, >= degil"


# ------------------------------------------------ below the bar nothing is said

def test_a_thin_sample_is_never_warned_on_however_lopsided():
    summary = _summarise(_rows(adverse=MIN_SAMPLES_FOR_SYMMETRY - 1, favourable=0))
    assert not _verdict(summary)


# ------------------------------------------------------------ degenerate shapes

def test_no_samples_at_all():
    assert _summarise([]) == {"samples": 0}
    assert not _verdict({"samples": 0})


def test_every_fill_exactly_on_the_requested_price():
    summary = _summarise(_rows(exact=MIN_SAMPLES_FOR_SYMMETRY))
    assert summary["adverse"] == 0 and summary["favourable"] == 0
    assert summary["adverse_ratio"] == 0.0
    assert not _verdict(summary), "kusursuz dolum serisi isaretlendi"


def test_only_favourable_fills():
    summary = _summarise(_rows(favourable=MIN_SAMPLES_FOR_SYMMETRY))
    assert summary["adverse_ratio"] == 0.0
    assert not _verdict(summary)


def test_the_ratio_stays_json_safe():
    """It is serialised into /api/state; Infinity is not valid JSON."""
    import json
    for rows in (_rows(adverse=100), _rows(adverse=1), _rows(exact=5)):
        encoded = json.dumps(_summarise(rows))
        assert "Infinity" not in encoded and "NaN" not in encoded, encoded


def test_the_threshold_constant_is_still_a_ratio():
    assert MAX_ADVERSE_RATIO > 1.0
