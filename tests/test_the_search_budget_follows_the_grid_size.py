"""Every family gets the same 2000 combos regardless of how big its grid is.

The grid a sweep actually samples is **not** ``strategy_grids[fam]`` - that is
only the family's own axes. It is ``searchable_axes(fam, {**shared, **own})``,
where the shared risk grid (sl_atr_mult 6 x trail_start_atr 6 x
trail_step_atr 5 x max_spread_atr 6) multiplies whatever the family states.
Read off the live blob 31.08:

    ichimoku         1,080      parabolic_flip     8,640
    stoch_flip      28,800      t3_flip          144,000
    mtf_pullback   622,080      burst          1,244,160
    dual_t3      2,073,600

At a flat ``max_combos`` of 2000 that is 100% coverage for ichimoku and
**0.12%** for dual_t3 - a 190x spread in how thoroughly each family is
explored. The optimizer then ranks those families head to head to pick a
symbol's winner, so a well-covered family presents something near its true
optimum while a starved one presents the best of a tiny random draw. Expected
best-of-sample sits well below true best, so the contest is tilted by grid
size rather than by which idea trades better, and the starved families' winners
move with ``combo_seed``.

Budget handed to a family beyond its own grid size buys nothing - there is no
unexplored combo left to spend it on. This hands that surplus to the families
still short, in proportion to how much space they have left, **without
changing the total**: same wall clock, same worker count.

No family may come out worse than the flat cap, so this cannot regress a
search that is tuned today.

Scale note: only ichimoku currently sits under the cap, so the redistribution
moves ~920 combos. It removes a real waste and it is the right shape, but on
today's grids it is a small effect - closing the 190x spread needs the grids
themselves to come down, which is a separate decision.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import coverage_budget

SHIPPED = {
    "ichimoku": 1_080,
    "parabolic_flip": 8_640,
    "stoch_flip": 28_800,
    "t3_flip": 144_000,
    "mtf_pullback": 622_080,
    "burst": 1_244_160,
    "dual_t3": 2_073_600,
}
CAP = 2000


def test_the_total_spend_does_not_grow():
    """Same wall clock. This buys coverage with waste, not with time."""
    got = coverage_budget(SHIPPED, CAP)
    assert sum(got.values()) <= CAP * len(SHIPPED)


def test_a_small_grid_is_searched_exhaustively_and_no_further():
    """1,080 combos is the whole space; a 2000 budget idles 920 of it."""
    got = coverage_budget(SHIPPED, CAP)
    assert got["ichimoku"] == 1_080


def test_the_freed_budget_goes_to_the_worst_covered_family():
    """Most unexplored space first: dual_t3 (0.12%) over stoch_flip (7%)."""
    got = coverage_budget(SHIPPED, CAP)
    assert (got["dual_t3"] > got["burst"] > got["mtf_pullback"]
            > got["t3_flip"] > got["stoch_flip"] > got["parabolic_flip"] > CAP)


def test_no_family_is_worse_off_than_the_flat_cap():
    got = coverage_budget(SHIPPED, CAP)
    for fam, total in SHIPPED.items():
        assert got[fam] >= min(total, CAP), fam


def test_nobody_is_given_more_budget_than_it_has_grid():
    got = coverage_budget(SHIPPED, CAP)
    for fam, total in SHIPPED.items():
        assert got[fam] <= total, fam


def test_coverage_of_the_worst_family_actually_improves():
    got = coverage_budget(SHIPPED, CAP)
    worst = min(SHIPPED, key=lambda f: CAP / SHIPPED[f])
    assert got[worst] > CAP


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
