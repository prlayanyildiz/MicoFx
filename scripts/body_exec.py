"""min_body_ratio upgrades from charged holdout - entry filter only.

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

BODY_CANDIDATES: tuple[float, ...] = (0.0, 0.1, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)

AXIS = Axis(
    field="min_body_ratio",
    live_key="live_body",
    candidates=BODY_CANDIDATES,
    label="min_body_ratio",
)


def best_body_upgrade(
    live_body: float,
    scored: dict[float, dict[str, Any] | None],
    **kw: Any,
) -> dict[str, Any] | None:
    return best_axis_upgrade(AXIS, live_body, scored, **kw)


def propose_body_upgrade(row: dict[str, Any]) -> dict[str, Any] | None:
    return propose_axis_upgrade(AXIS, row)


def apply_body_upgrade(
    headers: dict[str, str], *, panel: str, row: dict[str, Any],
) -> tuple[bool, str]:
    # propose_body_upgrade by name, not by value: this module is the
    # seam callers patch and override.
    return apply_axis_upgrade(AXIS, headers, panel=panel, row=row,
                              propose=propose_body_upgrade)


def _score_body(
    row: dict[str, Any], vals: tuple[float, ...],
) -> dict[float, dict[str, Any] | None]:
    """Kept for callers that scored an axis directly before the merge."""
    return score_axis(AXIS, row, vals)
