"""Anchored WFO apply-gate helpers (queued; not live-wired)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.wfo_apply_gate import anchored_wfo_apply_ok, distinct_param_sets


def test_rejects_negative_oos():
    params = [{"a": 1}] * 5
    assert not anchored_wfo_apply_ok(oos_sum_r=-30.9, fold_params=params)


def test_rejects_unstable_params():
    # 4 distinct / 5 folds — Claude sweep GER40 pattern
    params = [{"x": i} for i in (1, 2, 3, 4, 1)]
    assert distinct_param_sets(params) == 4
    assert not anchored_wfo_apply_ok(oos_sum_r=11.0, fold_params=params)


def test_accepts_stable_positive_oos():
    # XAU min_body: 1 set / 5 folds, OOS +26.9
    params = [{"min_body_ratio": 0.1}] * 5
    assert anchored_wfo_apply_ok(oos_sum_r=26.9, fold_params=params)


def test_rejects_too_few_folds():
    assert not anchored_wfo_apply_ok(
        oos_sum_r=10.0, fold_params=[{"a": 1}] * 4, min_folds=5
    )
