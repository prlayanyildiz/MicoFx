"""window_reconcile — holdout vs slice agreement for field upgrades."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.window_reconcile import decide_windows


def test_decide_apply_when_both_agree():
    assert decide_windows(
        slice_live_sum=100, slice_chal_sum=160, slice_robust=True,
        hold_live=200, hold_chal=220,
    ) == "APPLY"


def test_decide_conflict_frontload():
    """XAU min_body pattern: slice sum up, holdout down."""
    assert decide_windows(
        slice_live_sum=471, slice_chal_sum=521, slice_robust=True,
        hold_live=250.71, hold_chal=241.63,
    ) == "KEEP_CONFLICT_frontload"


def test_decide_keep_when_holdout_wins():
    assert decide_windows(
        slice_live_sum=100, slice_chal_sum=90, slice_robust=False,
        hold_live=250, hold_chal=240,
    ) == "KEEP"


def test_decide_hold_only_review():
    """Recent holdout likes challenger; full-history slice does not."""
    assert decide_windows(
        slice_live_sum=200, slice_chal_sum=190, slice_robust=False,
        hold_live=100, hold_chal=120,
    ) == "HOLD_ONLY_review"
