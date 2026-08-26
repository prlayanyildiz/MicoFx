"""14-day deals_since must not sit in the middle of _cycle.

review() fetches lookback history under the shared MT5 lock. Running it
before evaluate/entry stretched every other symbol's trail. Kick it off
the critical path; quarantine can lag one interval (already 120s).
"""
from __future__ import annotations

from pathlib import Path


def test_cycle_does_not_call_review_inline():
    src = Path("micofx/engine.py").read_text(encoding="utf-8")
    cycle = src.split("def _cycle(", 1)[1].split("\n    def ", 1)[0]
    assert "self.supervisor.review(" not in cycle
    assert "_kick_supervisor_review" in cycle


def test_kick_does_not_wait_for_the_history_fetch():
    src = Path("micofx/engine.py").read_text(encoding="utf-8")
    kick = src.split("def _kick_supervisor_review(", 1)[1].split("\n    def ", 1)[0]
    assert "daemon=True" in kick
    assert "self.supervisor.review" not in kick or "Thread" in kick
