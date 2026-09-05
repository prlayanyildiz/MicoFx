"""book_robust_audit floors + markdown."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.book_robust_audit import audit_row, audit_rows, floor_for, markdown_table


def _rep(nets, *, valid=None):
    valid = valid or [True] * len(nets)
    wins = sum(1 for n, ok in zip(nets, valid, strict=True) if ok and n > 0)
    return {
        "nets": nets,
        "valid": valid,
        "valid_n": sum(1 for ok in valid if ok),
        "wins_valid": wins,
    }


def test_fragile_floors():
    assert floor_for("JPN225") == 2
    assert floor_for("SpotBrent") == 3
    assert floor_for("NAS100") == 4


def test_audit_row_flags_below_floor():
    row = {"symbol": "NAS100", "enabled": True, "timeframe": "M30"}
    with patch(
        "scripts.book_robust_audit.charged_slice_report",
        return_value=_rep([1.0, -1.0, -1.0, -1.0, 1.0, 10.0]),  # 3/6
    ):
        out = audit_row(row)
    assert out["ok"] is False
    assert out["wins"] == 3


def test_jpn_at_fragile_floor_ok():
    row = {"symbol": "JPN225", "enabled": True}
    with patch(
        "scripts.book_robust_audit.charged_slice_report",
        return_value=_rep([-17.0, -5.0, 0.0, -3.0, 12.0, 151.0]),  # 2/6
    ):
        out = audit_row(row)
    assert out["ok"] is True
    assert out["wins"] == 2


def test_markdown_and_audit_rows_skip_disabled():
    rows = [
        {"symbol": "GER40", "enabled": True},
        {"symbol": "OFF", "enabled": False},
    ]
    with patch(
        "scripts.book_robust_audit.charged_slice_report",
        side_effect=lambda row, parts=6, **kw: (
            {**_rep([9.0, 16.0, 9.0, 26.0, 68.0, 54.0]), "parts": parts}
            if parts == 6
            else {**_rep([1.0] * 12), "parts": 12}
        ),
    ):
        out = audit_rows(rows)
    assert len(out) == 1
    assert out[0].get("wins_12") == 12
    md = markdown_table(out)
    assert "GER40" in md
    assert "12/12" in md
    assert "wins12" in md.lower() or "| 12/12 |" in md


def test_alert_erosion_writes_wake_and_inbox(tmp_path):
    from scripts.book_robust_audit import alert_erosion

    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    results = [{
        "symbol": "NAS100", "ok": False, "wins": 3, "parts": 6,
        "floor": 4, "sum_r": 10.0, "nets": [1, -1, -1, -1, 1, 10],
        "note": "ALTINDA",
    }]
    notes = alert_erosion(
        results, wake_path=wake, cursor_inbox=inbox)
    assert notes and wake.is_file()
    text = inbox.read_text(encoding="utf-8")
    assert "EROZYON" in text and "NAS100" in text
