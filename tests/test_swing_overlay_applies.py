"""The swing exit overlay must actually reach the search.

``SWING_GRID_OVERLAY`` exists to widen the stop and trail axes once the bars get
long. Its own comment states what happens without it: "the search only ever
offers H1 candidates a stop tight enough to be noise". The build merged it the
wrong way round:

    grid = dict(SWING_GRID_OVERLAY) if uses_swing_exits(family, tf) else {}
    grid.update(variant["grid"])

with the stated intent "Swing overlay first, then the family's own grid on top:
a family that states its own stop/trail range means it". But ``variant["grid"]``
is not the family's own grid - it is ``{**shared, **family_grid}``. The shared
grid defines all four overlay axes (sl_atr_mult, trail_start_atr,
trail_step_atr, max_spread_atr), so it overwrote the overlay for every family on
every timeframe. The overlay was inert.

Visible in what the search returned: FRA40 came back with burst/M30 carrying
``sl_atr_mult = 0.5`` - half the overlay's own minimum of 1.0, and a value that
only exists in the shared grid - on thirty-minute bars. USDJPY took burst/M30 at
0.7 with ``trail_start_atr = 0.5``, under the overlay's 0.6 floor.

The precedence the comment describes is shared -> overlay -> the family's own
statement. That is what it does now: the overlay widens what the shared grid
proposes, and steps aside for any axis the family has an opinion about.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SWING_GRID_OVERLAY, uses_swing_exits


def _merge(shared: dict, own: dict, family: str, tf: str) -> dict:
    """The optimizer's own merge, lifted so it can be asserted directly."""
    from micofx.optimizer import Optimizer
    return Optimizer._exit_grid_for({**shared, **own}, own, family, tf)


SHARED = {
    "sl_atr_mult": [0.5, 0.7, 0.9, 1.2, 1.5, 2],
    "trail_start_atr": [0.3, 0.4, 0.5, 0.7, 1, 1.4, 2],
    "trail_step_atr": [0.25, 0.4, 0.6, 0.8, 1.2, 1.6, 2.2],
    "max_spread_atr": [0.0, 0.05, 0.08, 0.12, 0.18],
}
OWN = {"brst_lookback": [10, 20], "brst_range_z": [1.0, 2.0]}


# ------------------------------------------------------------- the defect

@pytest.mark.parametrize("tf", ["M15", "M30"])
@pytest.mark.parametrize("axis", sorted(SWING_GRID_OVERLAY))
def test_the_overlay_reaches_the_search_on_long_bars(tf, axis):
    grid = _merge(SHARED, OWN, "burst", tf)
    assert grid[axis] == SWING_GRID_OVERLAY[axis], (
        f"{axis} hala paylasilan izgaradan geliyor, overlay ezilmis")


def test_a_thirty_minute_stop_cannot_be_half_the_overlay_floor():
    """FRA40 came back with sl_atr_mult 0.5 on M30; 0.5 exists only in shared."""
    grid = _merge(SHARED, OWN, "burst", "M30")
    assert 0.5 not in grid["sl_atr_mult"]
    assert min(grid["sl_atr_mult"]) == 1.0


def test_the_trail_start_floor_holds():
    """USDJPY came back with trail_start_atr 0.5, under the overlay's 0.6."""
    grid = _merge(SHARED, OWN, "burst", "M30")
    assert min(grid["trail_start_atr"]) == 0.6


# --------------------------------------------- what the comment promised

def test_a_family_that_states_its_own_range_still_wins():
    own = dict(OWN, sl_atr_mult=[4.0, 5.0])
    grid = _merge(SHARED, own, "burst", "M30")
    assert grid["sl_atr_mult"] == [4.0, 5.0], "ailenin kendi beyani ezilmis"
    # ...while the axes it said nothing about still get widened.
    assert grid["trail_step_atr"] == SWING_GRID_OVERLAY["trail_step_atr"]


def test_short_bars_keep_the_shared_grid():
    grid = _merge(SHARED, OWN, "burst", "M5")
    assert uses_swing_exits("burst", "M5") is False
    for axis in SWING_GRID_OVERLAY:
        assert grid[axis] == SHARED[axis], f"{axis} M5'te genisletilmis"


def test_the_family_parameters_survive_either_way():
    for tf in ("M5", "M30"):
        grid = _merge(SHARED, OWN, "burst", tf)
        assert grid["brst_lookback"] == [10, 20]
        assert grid["brst_range_z"] == [1.0, 2.0]


def test_an_axis_only_the_overlay_knows_is_still_added():
    grid = _merge({"sl_atr_mult": [0.5]}, {}, "t3_stoch", "M30")
    assert grid["trail_step_atr"] == SWING_GRID_OVERLAY["trail_step_atr"]
