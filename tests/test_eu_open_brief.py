"""eu_open_brief — one-shot readiness wake at broker h>=7."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.eu_open_brief import maybe_brief


def test_brief_waits_before_hour(tmp_path):
    assert maybe_brief(
        broker_h=6, state_path=tmp_path / "s.json",
        wake_path=tmp_path / "W.txt",
        cursor_inbox=tmp_path / "I.md") == []


def test_brief_once_per_day(tmp_path):
    st = tmp_path / "s.json"
    wake = tmp_path / "W.txt"
    inbox = tmp_path / "I.md"
    with patch("scripts.eu_open_brief.urllib.request"):
        a1 = maybe_brief(
            broker_h=7, state_path=st, wake_path=wake, cursor_inbox=inbox,
            panel="http://x")
        a2 = maybe_brief(
            broker_h=7, state_path=st, wake_path=wake, cursor_inbox=inbox,
            panel="http://x")
    assert a1 and not a2
    assert "EU-OPEN BRIEF" in inbox.read_text(encoding="utf-8")
