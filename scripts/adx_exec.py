"""adx_min upgrades from charged holdout - entry filter only.

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

ADX_MIN_CANDIDATES: tuple[float, ...] = (0.0, 10.0, 12.0, 15.0, 18.0, 20.0, 22.0, 25.0)

AXIS = Axis(
    field="adx_min",
    live_key="live_adx",
    candidates=ADX_MIN_CANDIDATES,
    label="adx_min",
)


def best_adx_upgrade(
    live_adx: float,
    scored: dict[float, dict[str, Any] | None],
    **kw: Any,
) -> dict[str, Any] | None:
    return best_axis_upgrade(AXIS, live_adx, scored, **kw)


def propose_adx_upgrade(row: dict[str, Any]) -> dict[str, Any] | None:
    return propose_axis_upgrade(AXIS, row)


def apply_adx_upgrade(
    headers: dict[str, str], *, panel: str, row: dict[str, Any],
) -> tuple[bool, str]:
    # propose_adx_upgrade by name, not by value: this module is the
    # seam callers patch and override.
    return apply_axis_upgrade(AXIS, headers, panel=panel, row=row,
                              propose=propose_adx_upgrade)


def _score_adx(
    row: dict[str, Any], vals: tuple[float, ...],
) -> dict[float, dict[str, Any] | None]:
    """Kept for callers that scored an axis directly before the merge."""
    return score_axis(AXIS, row, vals)
