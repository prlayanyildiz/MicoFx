"""cost_rank_max upgrades from charged holdout - entry filter only.

The rule lives in ``scripts/axis_exec.py``; this file is the axis. All four of
these were 177-line copies of one another, identical once the field name was
normalised away - same thresholds, same neighbour rule, same replay, same POST.
"""
from __future__ import annotations

from typing import Any

from scripts.axis_exec import (
    Axis,
    apply_axis_upgrade,
    best_axis_upgrade,
    propose_axis_upgrade,
    score_axis,
)

COST_RANK_CANDIDATES: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0)

AXIS = Axis(
    field="cost_rank_max",
    live_key="live_cr",
    candidates=COST_RANK_CANDIDATES,
    label="cost_rank",
)


def best_cost_rank_upgrade(
    live_cost_rank: float,
    scored: dict[float, dict[str, Any] | None],
    **kw: Any,
) -> dict[str, Any] | None:
    return best_axis_upgrade(AXIS, live_cost_rank, scored, **kw)


def propose_cost_rank_upgrade(row: dict[str, Any]) -> dict[str, Any] | None:
    return propose_axis_upgrade(AXIS, row)


def apply_cost_rank_upgrade(
    headers: dict[str, str], *, panel: str, row: dict[str, Any],
) -> tuple[bool, str]:
    # propose_cost_rank_upgrade by name, not by value: this module is the
    # seam callers patch and override.
    return apply_axis_upgrade(AXIS, headers, panel=panel, row=row,
                              propose=propose_cost_rank_upgrade)


def _score_cost_rank(
    row: dict[str, Any], vals: tuple[float, ...],
) -> dict[float, dict[str, Any] | None]:
    """Kept for callers that scored an axis directly before the merge."""
    return score_axis(AXIS, row, vals)
