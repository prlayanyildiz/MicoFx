"""panel_health_watch — one-shot panel-down wake."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.panel_health_watch import maybe_alert


def test_alerts_once_while_down_clears_on_recover(tmp_path):
    st = tmp_path / "panel.json"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    a1 = maybe_alert(
        ok=False, state_path=st, wake_path=wake, cursor_inbox=inbox)
    a2 = maybe_alert(
        ok=False, state_path=st, wake_path=wake, cursor_inbox=inbox)
    assert a1 and not a2
    assert "PANEL DOWN" in inbox.read_text(encoding="utf-8")
    assert maybe_alert(
        ok=True, state_path=st, wake_path=wake, cursor_inbox=inbox) == []
    a3 = maybe_alert(
        ok=False, state_path=st, wake_path=wake, cursor_inbox=inbox)
    assert a3  # new outage after recover can alert again
