"""Per-symbol blocked-hour seeds from autopsy fill_time (Claude #3)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import (
    blocked_hour_search_axis,
    weak_entry_hours_from_autopsy,
)


def _row(symbol: str, fill_hour: int, r: float, day: int = 1) -> dict:
    # Naive broker epoch: day*86400 + hour*3600
    return {
        "symbol": symbol,
        "fill_time": day * 86400 + fill_hour * 3600,
        "r_realised": r,
    }


def test_weak_hours_worst_first_for_symbol():
    rows = []
    # NAS100: hour 17 loses, hour 10 wins; hour 3 thin
    for d in range(1, 8):
        rows.append(_row("NAS100", 17, -1.0, d))
        rows.append(_row("NAS100", 10, 1.5, d))
        rows.append(_row("US30", 17, -1.0, d))  # other symbol
    rows.append(_row("NAS100", 3, -1.0, 1))  # n=1, ignored
    weak = weak_entry_hours_from_autopsy(rows, "NAS100", min_n=5)
    assert weak[0] == 17
    assert 10 not in weak


def test_weak_hours_falls_back_empty_when_thin():
    assert weak_entry_hours_from_autopsy([], "NAS100") == []
    assert weak_entry_hours_from_autopsy(
        [_row("NAS100", 11, -1.0)], "NAS100") == []


def test_axis_uses_symbol_weak_over_book_default():
    axis = blocked_hour_search_axis(weak_hours=[16, 13], live_blocked=[])
    assert axis[0] == []
    assert [16] in axis
    assert sorted([13, 16]) in [sorted(x) for x in axis]
