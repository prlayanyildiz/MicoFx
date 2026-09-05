"""us30_fill_watch — post-restart fill vs spread (report-only)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.us30_fill_watch import (
    _load,
    arm_session_day,
    evaluate_row,
    maybe_alert,
    snapshot,
)


def test_evaluate_poor_fill_needs_enough_signals():
    thin = evaluate_row({
        "symbol": "US30", "signals": 3, "opened": 0,
        "fill_rate": 0.0, "blocks": {"spread": 3},
    })
    assert thin["poor_fill"] is False
    early = evaluate_row({
        "symbol": "US30", "signals": 4, "opened": 0,
        "fill_rate": 0.0, "blocks": {"spread": 4},
    }, min_signals=4)
    assert early["poor_fill"] is True
    fat = evaluate_row({
        "symbol": "US30", "signals": 10, "opened": 2,
        "fill_rate": 0.2, "blocks": {"spread": 7},
    })
    assert fat["poor_fill"] is True
    ok = evaluate_row({
        "symbol": "US30", "signals": 10, "opened": 8,
        "fill_rate": 0.8, "blocks": {"spread": 1},
    })
    assert ok["poor_fill"] is False


def test_evaluate_ignores_seans_disi_for_poor_fill():
    """Out-of-session tallies must not fake a spread-gate miss."""
    noise = evaluate_row({
        "symbol": "NAS100", "signals": 8, "opened": 0,
        "fill_rate": 0.0,
        "blocks": {"seans_disi": 8},
    }, min_signals=4)
    assert noise["actionable_signals"] == 0
    assert noise["poor_fill"] is False
    mixed = evaluate_row({
        "symbol": "NAS100", "signals": 8, "opened": 0,
        "fill_rate": 0.0,
        "blocks": {"seans_disi": 4, "spread": 4},
    }, min_signals=4)
    assert mixed["actionable_signals"] == 4
    assert mixed["poor_fill"] is True


def test_evaluate_ignores_saat_kapali_for_poor_fill():
    soft = evaluate_row({
        "symbol": "JPN225", "signals": 8, "opened": 0,
        "fill_rate": 0.0, "blocks": {"saat_kapali": 8},
    }, min_signals=4)
    assert soft["actionable_signals"] == 0
    assert soft["poor_fill"] is False


def test_arm_session_day_once(tmp_path):
    path = tmp_path / "nas.json"
    path.write_text('{"alerted": true, "alerted_at": "x"}', encoding="utf-8")
    assert arm_session_day(path, day_key="2026-09-04") is True
    st = _load(path)
    assert st["session_day"] == "2026-09-04"
    assert st["alerted"] is False
    assert "alerted_at" not in st
    assert arm_session_day(path, day_key="2026-09-04") is False
    assert _load(path)["alerted"] is False


def test_maybe_alert_dedupes(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "scripts.us30_fill_watch.fetch_us30_row",
        lambda *a, **k: {
            "symbol": "US30", "signals": 12, "opened": 2,
            "fill_rate": 0.16, "blocks": {"spread": 9}, "retries": {},
        },
    )
    state = tmp_path / "us30.json"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    rep = snapshot("http://x", state_path=state)
    assert rep["poor_fill"]
    first = maybe_alert(
        rep, state_path=state, wake_path=wake, cursor_inbox=inbox)
    assert first and wake.is_file()
    assert "US30 FILL ALERT" in inbox.read_text(encoding="utf-8")
    assert maybe_alert(
        rep, state_path=state, wake_path=wake, cursor_inbox=inbox) == []
