"""The trail grid must not cap below where the search keeps landing.

Measured on the live portfolio before this change: 8 of 23 optimised symbols
(35%) held trail_start_atr at 1.4, which was the largest value any grid offered,
and 4 held trail_step_atr at its own maximum of 1.6. A third of the book sitting
exactly on a boundary is the search saying it wanted to go further and could
not - the ceiling was choosing the parameter, not the data.

sl_atr_mult is deliberately left alone: nothing sat at its maximum and four
symbols chose its minimum, so the hard stop is genuinely where the walk-forward
wants it. This is about the trail only.

Nothing here sets a value. The grid is the search space; every candidate still
has to clear the same out-of-sample gates, beat its incumbent and hold its
holdout retention before it can replace a live config.
"""
from __future__ import annotations

from micofx.models import OPT_FIELDS
from micofx.paths import load_defaults

TRAIL_AXES = ("trail_start_atr", "trail_step_atr")

# What the incumbents were pinned at, i.e. what the grid must now reach past.
PREVIOUS_CEILING = {"trail_start_atr": 1.4, "trail_step_atr": 1.6}


def _grids():
    """Every grid the optimizer can search: the shared one plus per-family."""
    opt = load_defaults()["optimizer"]
    yield "shared", opt["grid"]
    yield from (opt.get("strategy_grids") or {}).items()


def test_every_trail_axis_reaches_past_the_old_ceiling():
    seen = 0
    for name, axes in _grids():
        for axis in TRAIL_AXES:
            values = axes.get(axis)
            if not values:
                continue
            seen += 1
            assert max(values) > PREVIOUS_CEILING[axis], (
                f"{name}.{axis} still caps at {max(values)} - symbols pinned "
                f"there cannot express a looser trail")
    assert seen >= 2, "no trail axes found; grid layout changed"


def test_the_tight_end_is_untouched():
    # Widening the ceiling must not quietly drop the tight settings that some
    # symbols genuinely validated on.
    shared = load_defaults()["optimizer"]["grid"]
    assert min(shared["trail_start_atr"]) == 0.3
    assert min(shared["trail_step_atr"]) == 0.25


def test_the_hard_stop_grid_is_not_widened():
    # Deliberate: the evidence pointed at the trail, not the stop. sl_atr_mult
    # also feeds lot sizing, so moving it is a risk change, not a search change.
    assert max(load_defaults()["optimizer"]["grid"]["sl_atr_mult"]) == 2.0


def test_axes_stay_sorted_and_unique():
    for name, axes in _grids():
        for axis in TRAIL_AXES:
            values = axes.get(axis)
            if not values:
                continue
            assert values == sorted(values), f"{name}.{axis} not ascending"
            assert len(values) == len(set(values)), f"{name}.{axis} has duplicates"


def test_trail_axes_are_still_writable_by_the_optimizer():
    # A grid axis the search cannot legally apply to a SymbolConfig is dead
    # weight - store.opt_params() filters exactly this way.
    for axis in TRAIL_AXES:
        assert axis in OPT_FIELDS
