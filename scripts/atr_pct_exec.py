"""atr_pct_min upgrades from charged holdout - entry filter only.

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

ATR_PCT_CANDIDATES: tuple[float, ...] = (0.0, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)

AXIS = Axis(
    field="atr_pct_min",
    live_key="live_atr_pct",
    candidates=ATR_PCT_CANDIDATES,
    label="atr_pct_min",
)


def best_atr_pct_upgrade(
    live_atr_pct: float,
    scored: dict[float, dict[str, Any] | None],
    **kw: Any,
) -> dict[str, Any] | None:
    return best_axis_upgrade(AXIS, live_atr_pct, scored, **kw)


def propose_atr_pct_upgrade(row: dict[str, Any]) -> dict[str, Any] | None:
    return propose_axis_upgrade(AXIS, row)


def apply_atr_pct_upgrade(
    headers: dict[str, str], *, panel: str, row: dict[str, Any],
) -> tuple[bool, str]:
    # propose_atr_pct_upgrade by name, not by value: this module is the
    # seam callers patch and override.
    return apply_axis_upgrade(AXIS, headers, panel=panel, row=row,
                              propose=propose_atr_pct_upgrade)


def _score_atr_pct(
    row: dict[str, Any], vals: tuple[float, ...],
) -> dict[float, dict[str, Any] | None]:
    """Kept for callers that scored an axis directly before the merge."""
    return score_axis(AXIS, row, vals)
