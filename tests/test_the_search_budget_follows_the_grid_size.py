"""Every family gets the same 2000 combos regardless of how big its grid is.

The grid a sweep actually samples is **not** ``strategy_grids[fam]`` - that is
only the family's own axes. It is ``searchable_axes(fam, {**shared, **own})``,
where the shared risk grid (sl_atr_mult 6 x trail_start_atr 6 x
trail_step_atr 5 x max_spread_atr 6) multiplies whatever the family states.
Read off the live five-family blob 01.09:

    ichimoku        12,960      (entry gates + exits; was exit-only 1,080)
    channel_break   14,580      mtf_pullback     622,080
    burst        1,244,160

At a flat ``max_combos`` of 2000 ichimoku now samples ~15% of its grid
(entry gates landed 02.09); burst is still ~0.16%. Budget redistribution
only fires when a family's grid is smaller than the cap.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import coverage_budget

SHIPPED = {
    "ichimoku": 12_960,
    "channel_break": 14_580,
    "mtf_pullback": 622_080,
    "burst": 1_244_160,
}
CAP = 2000


def test_the_total_spend_does_not_grow():
    """Same wall clock. This buys coverage with waste, not with time."""
    got = coverage_budget(SHIPPED, CAP)
    assert sum(got.values()) <= CAP * len(SHIPPED)


def test_a_small_grid_is_searched_exhaustively_and_no_further():
    """A grid under the cap spends only what it needs."""
    got = coverage_budget({"tiny": 500, "big": 50_000}, CAP)
    assert got["tiny"] == 500


def test_the_freed_budget_goes_to_the_worst_covered_family():
    """Surplus from a tiny grid flows to the biggest unexplored family."""
    got = coverage_budget({"tiny": 500, "mid": 50_000, "burst": 1_244_160}, CAP)
    assert got["tiny"] == 500
    assert got["burst"] > got["mid"] > CAP


def test_no_family_is_worse_off_than_the_flat_cap():
    got = coverage_budget(SHIPPED, CAP)
    for fam, total in SHIPPED.items():
        assert got[fam] >= min(total, CAP), fam


def test_nobody_is_given_more_budget_than_it_has_grid():
    got = coverage_budget(SHIPPED, CAP)
    for fam, total in SHIPPED.items():
        assert got[fam] <= total, fam


def test_coverage_of_the_worst_family_actually_improves():
    got = coverage_budget({"tiny": 500, "burst": 1_244_160}, CAP)
    assert got["burst"] > CAP


# ------------------------------------------------------------ degenerate

def test_all_families_already_exhaustive_spends_only_what_is_needed():
    got = coverage_budget({"a": 10, "b": 20}, CAP)
    assert got == {"a": 10, "b": 20}


def test_no_small_family_means_nothing_to_redistribute():
    """Every grid over the cap: the flat cap is already the honest answer."""
    got = coverage_budget({"a": 50_000, "b": 60_000}, CAP)
    assert got == {"a": CAP, "b": CAP}


def test_an_empty_family_map_is_not_a_crash():
    assert coverage_budget({}, CAP) == {}


def test_a_nonsense_cap_falls_back_to_the_grid():
    got = coverage_budget({"a": 100}, 0)
    assert got["a"] >= 0
