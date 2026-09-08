"""Concurrent per-symbol ticket alarm (scale-in aware)."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.concurrent_stack_watch import (
    counts_by_symbol,
    evaluate,
    maybe_alert,
    snapshot_from_positions,
)


def test_evaluate_respects_max_positions_caps():
    assert evaluate({"BTCUSD": 1, "NAS100": 1})["fire"] is False
    # Legal XAU scale-in at cap 5
    ok = evaluate({"XAUUSD": 3}, caps={"XAUUSD": 5})
    assert ok["fire"] is False
    # Breach only above cap
    bad = evaluate({"JPN225": 3}, caps={"JPN225": 2})
    assert bad["fire"] is True
    assert bad["offenders"] == {"JPN225": 3}
    assert bad["max_concurrent"] == 3


def test_evaluate_unknown_symbol_allows_up_to_five():
    # No cap map → book max 5 (do not false-alarm legal stacks)
    assert evaluate({"US30": 2})["fire"] is False
    assert evaluate({"US30": 6})["fire"] is True


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
    snap = snapshot_from_positions(
        [
            {"config_symbol": "US30", "ticket": 10},
            {"config_symbol": "US30", "ticket": 11},
            {"config_symbol": "US30", "ticket": 12},
        ],
        caps={"US30": 2},
    )
    assert snap["fire"] is True
    first = maybe_alert(
        snap, state_path=state, wake_path=wake, cursor_inbox=inbox)
    assert first and wake.is_file()
    assert "max_positions" in inbox.read_text(encoding="utf-8")
    assert maybe_alert(
        snap, state_path=state, wake_path=wake, cursor_inbox=inbox) == []
    # Clear when back under cap
    clear = snapshot_from_positions(
        [{"config_symbol": "US30", "ticket": 10}],
        caps={"US30": 2},
    )
    maybe_alert(clear, state_path=state, wake_path=wake, cursor_inbox=inbox)
    st = json.loads(state.read_text(encoding="utf-8"))
    assert st.get("alerted") is False
