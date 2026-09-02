"""Research scanner produces constitution-safe curated ideas."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import research_scanner as rs


def test_curated_ideas_skip_banned_patterns():
    ideas = rs._curated_ideas(["GER40", "US30"])
    blob = " ".join(str(i.get("title", "")) + str(i.get("snippet", "")) for i in ideas)
    assert "lstm" not in blob.lower()
    assert "stoch_flip" not in blob.lower()
    assert len(ideas) >= 3


def test_render_includes_active_symbols():
    report = {
        "ts": "2026-01-01 12:00:00",
        "topic": "test",
        "active_symbols": ["NAS100"],
        "items": [{"source": "mico", "title": "T", "snippet": "S", "score": 1.0, "action": "keep"}],
    }
    md = rs.render(report)
    assert "NAS100" in md
    assert "AR-GE" in md
