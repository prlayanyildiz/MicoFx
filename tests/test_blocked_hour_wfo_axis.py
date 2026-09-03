"""blocked_entry_hours as a real WFO axis (Claude 03.09 23:36 bleed #3).

Mechanism already enforced in session_mask / walk_forward probe, but every
live symbol kept []. Search must price discrete hour-sets so chop-death
hours (book 9h/11h/14h) can win apply.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import OPT_FIELDS
from micofx.optimizer import blocked_hour_search_axis
from micofx.strategy import ENGINE_OPT_FIELDS, searchable_axes


def test_blocked_hours_is_opt_and_engine_axis():
    assert "blocked_entry_hours" in OPT_FIELDS
    assert "blocked_entry_hours" in ENGINE_OPT_FIELDS


def test_searchable_axes_keeps_blocked_hours():
    grid = searchable_axes("mtf_pullback", {
        "sl_atr_mult": [1.0],
        "blocked_entry_hours": [[], [11], [9, 11]],
        "t3_length": [5],  # unread by mtf — dropped if in OPT
    })
    assert "blocked_entry_hours" in grid
    assert grid["blocked_entry_hours"] == [[], [11], [9, 11]]


def test_blocked_hour_axis_always_includes_empty():
    axis = blocked_hour_search_axis(weak_hours=[11, 9, 14])
    assert [] in axis
    assert axis[0] == []
    assert [11] in axis
    assert [9, 11] in axis or sorted([9, 11]) in [sorted(x) for x in axis]
    assert len(axis) <= 4


def test_blocked_hour_axis_includes_live_block():
    axis = blocked_hour_search_axis(
        weak_hours=[11, 9], live_blocked=[14])
    keys = {tuple(x) for x in axis}
    assert () in keys
    assert (14,) in keys


def test_blocked_hour_axis_caps_sets():
    axis = blocked_hour_search_axis(
        weak_hours=[11, 9, 14, 6, 3, 17], max_sets=3)
    assert len(axis) == 3
    assert axis[0] == []
