"""Operator-widened stop search must not be overwritten by the swing overlay.

Found after the morning book resize: SpotBrent/JPN225 (M5) took sl 4.0 / 2.5
and costed expectancy flipped, but the eight M15/M30 symbols stayed at 1.0-1.5.
``SWING_GRID_OVERLAY`` replaces every shared exit axis the family did not name,
including the operator's panel ``grid.sl_atr_mult``. The overlay floor is 1.0,
so a saved [1.5, 2, 3, 4] still produced 1.0 on M30 and the search picked the
tight end.

The overlay stays for axes the operator never changed from the shipped default
(that is the FRA40 0.5-on-M30 defect). Family ``own`` still wins both.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SWING_GRID_OVERLAY
from micofx.optimizer import Optimizer

FACTORY = {
    "sl_atr_mult": [0.5, 0.7, 0.9, 1.2, 1.5, 2.0],
    "trail_start_atr": [0.3, 0.4, 0.5, 0.7, 1.0, 1.4, 2.0],
    "trail_step_atr": [0.25, 0.4, 0.6, 0.8, 1.2, 1.6, 2.2],
    "max_spread_atr": [0.05, 0.08, 0.12, 0.18],
}

OPERATOR_SL = [1.5, 2.0, 2.5, 3.0, 4.0]


def _grid(shared: dict, own: dict, family: str, tf: str) -> dict:
    return Optimizer._exit_grid_for(
        {**shared, **own}, own, family, tf, shared=shared, factory=FACTORY)


def test_operator_sl_on_m30_must_not_contain_overlay_floor():
    """Panel set sl_atr_mult=[1.5,...]; M30 search still offered overlay 1.0."""
    shared = {**FACTORY, "sl_atr_mult": list(OPERATOR_SL)}
    grid = _grid(shared, {}, "t3_stoch", "M30")
    assert 1.0 not in grid["sl_atr_mult"]
    assert grid["sl_atr_mult"] == OPERATOR_SL


def test_untouched_shared_axes_still_take_the_overlay():
    """Operator only widened sl; trail/spread stay factory so overlay applies."""
    shared = {**FACTORY, "sl_atr_mult": list(OPERATOR_SL)}
    grid = _grid(shared, {}, "burst", "M30")
    assert grid["trail_start_atr"] == SWING_GRID_OVERLAY["trail_start_atr"]
    assert grid["trail_step_atr"] == SWING_GRID_OVERLAY["trail_step_atr"]
    assert grid["max_spread_atr"] == SWING_GRID_OVERLAY["max_spread_atr"]


def test_family_own_still_beats_operator_and_overlay():
    shared = {**FACTORY, "sl_atr_mult": list(OPERATOR_SL)}
    own = {"sl_atr_mult": [4.0, 5.0]}
    grid = _grid(shared, own, "burst", "M30")
    assert grid["sl_atr_mult"] == [4.0, 5.0]


def test_shipped_shared_on_m30_still_gets_overlay_floor():
    """FRA40 defect: factory scalp sl must not leak 0.5 onto M30."""
    grid = _grid(dict(FACTORY), {}, "burst", "M30")
    assert 0.5 not in grid["sl_atr_mult"]
    assert min(grid["sl_atr_mult"]) == 1.0
