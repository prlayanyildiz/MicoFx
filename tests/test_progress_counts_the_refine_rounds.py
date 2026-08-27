"""The panel's combo total must be the work actually being done.

``walk_forward`` spends ``max_combos * (1 + refine_rounds)`` backtests per
sweep - each refine round gets its own full budget, so the shipped
refine_rounds=3 makes a sweep cost 4x max_combos. The optimizer's progress
counter reported plain ``max_combos`` per sweep, so a live run showed
combo_total 1,120,000 against a real budget of 4,480,000.

The percentage was never wrong (both sides of the ratio used the same wrong
unit) - the absolute number a human reads was, by exactly 4x. One formula now
serves the code that spends the budget and the code that reports it, so the
two cannot drift apart again.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.backtest import sweep_budget


def test_the_shipped_settings_cost_four_times_max_combos():
    """2000 combos, 3 refine rounds - the live configuration on 13.08."""
    assert sweep_budget(2000, 3) == 8000


def test_a_refine_round_is_a_full_extra_budget_not_a_fraction():
    for rounds in range(0, 6):
        assert sweep_budget(1000, rounds) == 1000 * (1 + rounds)


def test_no_refining_costs_exactly_the_coarse_pass():
    assert sweep_budget(2500, 0) == 2500


def test_negative_rounds_do_not_shrink_the_budget_below_the_coarse_pass():
    """max(0, ...) guards this in walk_forward; the shared helper must agree."""
    assert sweep_budget(2000, -1) == 2000
    assert sweep_budget(2000, -99) == 2000


def test_walk_forward_spends_what_this_helper_reports():
    """The whole point of the shared helper: the two call sites must agree.

    Pinned by reading the budget walk_forward hands to its progress callback -
    if walk_forward ever computes its own total again, this catches the drift.
    """
    import inspect

    from micofx import backtest

    src = inspect.getsource(backtest.walk_forward)
    assert "sweep_budget(max_combos, refine_rounds)" in src, \
        "walk_forward must take its budget from the shared helper"
    assert "max_combos * (1 + max(0, refine_rounds))" not in src, \
        "the old inline formula is back - two paths, one policy broken"


def test_the_optimizer_reports_the_same_unit_it_spends():
    """The reporting side must not fall back to bare max_combos."""
    import inspect

    from micofx import optimizer

    src = inspect.getsource(optimizer.Optimizer._run_all)
    assert "run_combo_budget(" in src, \
        "progress must use the helper that honours family_max_combos"
    assert "combo_done=done_sweeps * max_combos" not in src, \
        "the fourfold undercount is back"
    assert "done_sweeps * per_sweep" not in src, \
        "global per_sweep understates a family with its own cap"


@pytest.mark.parametrize("max_combos,rounds,expected", [
    (2000, 3, 8000),
    (1500, 2, 4500),
    (500, 1, 1000),
])
def test_a_few_settings_someone_might_actually_pick(max_combos, rounds, expected):
    assert sweep_budget(max_combos, rounds) == expected
