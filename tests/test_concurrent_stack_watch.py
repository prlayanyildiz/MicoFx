"""Concurrent per-symbol ticket alarm (Claude 20:04)."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.concurrent_stack_watch import (
    counts_by_symbol,
    evaluate,
    max_concurrent_from_autopsy,
    maybe_alert,
    snapshot_from_positions,
)


def test_evaluate_fires_only_above_one():
    assert evaluate({"BTCUSD": 1, "NAS100": 1})["fire"] is False
    bad = evaluate({"JPN225": 2, "BTCUSD": 1})
    assert bad["fire"] is True
    assert bad["offenders"] == {"JPN225": 2}
    assert bad["max_concurrent"] == 2


def test_counts_by_symbol_prefers_config_symbol():
    pos = [
        {"symbol": "BTCUSD.a", "config_symbol": "BTCUSD", "ticket": 1},
        {"symbol": "BTCUSD.a", "config_symbol": "BTCUSD", "ticket": 2},
        {"symbol": "NAS100", "ticket": 3},
    ]
    assert counts_by_symbol(pos) == {"BTCUSD": 2, "NAS100": 1}


def test_maybe_alert_once_while_stacked(tmp_path: Path):
    state = tmp_path / "stack.json"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    snap = snapshot_from_positions([
        {"config_symbol": "US30", "ticket": 10},
        {"config_symbol": "US30", "ticket": 11},
    ])
    notes = maybe_alert(
        snap, state_path=state, wake_path=wake, cursor_inbox=inbox)
    assert any("STACK" in n or "stack" in n.lower() for n in notes)
    assert wake.is_file()
    assert "concurrent" in inbox.read_text(encoding="utf-8").lower()
    # Deduped while still stacked.
    assert maybe_alert(
        snap, state_path=state, wake_path=wake, cursor_inbox=inbox) == []
    # Clear latch when flat again so a later stack can re-alert.
    clear = snapshot_from_positions([{"config_symbol": "US30", "ticket": 10}])
    maybe_alert(clear, state_path=state, wake_path=wake, cursor_inbox=inbox)
    st = json.loads(state.read_text(encoding="utf-8"))
    assert st.get("alerted") is False


def test_max_concurrent_from_autopsy_overlap():
    # Two overlapping sells on JPN + one alone on BTC.
    rows = [
        {"symbol": "JPN225", "fill_time": 100.0, "exit_time": 200.0},
        {"symbol": "JPN225", "fill_time": 150.0, "exit_time": 250.0},
        {"symbol": "BTCUSD", "fill_time": 300.0, "exit_time": 400.0},
    ]
    rep = max_concurrent_from_autopsy(rows, last_n=25)
    assert rep["by_symbol"]["JPN225"] == 2
    assert rep["by_symbol"]["BTCUSD"] == 1
    assert rep["book_max"] == 2
