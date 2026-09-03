"""Search floors: sub-1.0 ATR stops reward bar-WFO but fail live autopsy.

Claude 03.09 23:21: premature-stop −58R on NAS0.5/JPN0.7/XAU0.5. Stored
opt_params keep old 0.5 via widen-merge, so defaults.json alone cannot
retire them — plan must filter the job grid.

JPN 04.09: floor 0.9 cliffs (−33R) while 0.8 is the sweet spot — ``keep``
re-injects live + one mid-step so WFO can name it without lowering the floor.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import floor_sl_atr_search_axis, sl_atr_search_keep


def test_floor_drops_sub_min_keeps_rest():
    assert floor_sl_atr_search_axis([0.5, 0.7, 0.9, 1.2, 1.5], floor=0.9) == [
        0.9, 1.2, 1.5]


def test_floor_fallback_when_all_too_tight():
    assert floor_sl_atr_search_axis([0.5, 0.7], floor=0.9) == [
        0.9, 1.2, 1.5, 2.0]


def test_floor_preserves_order_and_dedupes():
    assert floor_sl_atr_search_axis([1.5, 0.9, 1.5, 2.0], floor=0.9) == [
        1.5, 0.9, 2.0]


def test_keep_reinjects_live_and_mid_step_below_floor():
    assert sl_atr_search_keep(0.7, floor=0.9) == [0.7, 0.8]
    assert sl_atr_search_keep(0.8, floor=0.9) == [0.8]
    assert sl_atr_search_keep(1.2, floor=0.9) == [1.2]
    axis = floor_sl_atr_search_axis(
        [0.5, 0.7, 0.9, 1.2], floor=0.9, keep=sl_atr_search_keep(0.7))
    assert axis == [0.9, 1.2, 0.7, 0.8]
