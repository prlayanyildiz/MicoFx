"""Entry-block pressure helpers for spread exec recovery."""
from __future__ import annotations

from typing import Any


def spread_pressure(row: dict[str, Any] | None) -> int:
    """How strongly spread is blocking fills on this entry-block row.

    ``blocks.spread`` counts refuse *kinds* per signal window; while a bar
    signal stays live the engine also increments ``retries.spread`` every
    cycle. US30 04.09 night: 8 signals / 0 opens / blocks=2 / retries=879 —
    unique blocks alone never reach the autopilot/holdout_live threshold of
    10, so the exec gap stayed invisible.
    """
    if not isinstance(row, dict):
        return 0
    try:
        blocks = int((row.get("blocks") or {}).get("spread") or 0)
    except (TypeError, ValueError):
        blocks = 0
    try:
        retries = int((row.get("retries") or {}).get("spread") or 0)
    except (TypeError, ValueError):
        retries = 0
    return max(blocks, retries // 50)
