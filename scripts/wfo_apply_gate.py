"""Anchored WFO apply-gate helpers (Claude 13:52 / EK23 D1).

Not wired into ``upgrade_robust`` / live apply while baseline < 25 or
EXEC_PIPELINE_FROZEN (see ``.bridge/WFO_APPLY_GATE_QUEUE.json``).

Gate: OOS sum > 0 AND distinct param sets across folds <= max_distinct.
"""
from __future__ import annotations

import json
from typing import Any


def _param_key(params: Any) -> str:
    if isinstance(params, dict):
        return json.dumps(params, sort_keys=True, default=str)
    return str(params)


def distinct_param_sets(fold_params: list[Any]) -> int:
    """How many different parameter dicts appear across folds."""
    return len({_param_key(p) for p in fold_params})


def anchored_wfo_apply_ok(
    *,
    oos_sum_r: float,
    fold_params: list[Any],
    max_distinct: int = 2,
    min_folds: int = 5,
) -> bool:
    """True when OOS edge is positive and param choice is stable across folds.

    SpotBrent t3 passed 6-slice but OOS flipped −30.9R; sweep GER40 was
    +33R in-sample with 4 distinct sets / 5 folds (unstable). Both fail here.
    """
    if not (oos_sum_r > 0.0):
        return False
    if len(fold_params) < int(min_folds):
        return False
    return distinct_param_sets(fold_params) <= int(max_distinct)
