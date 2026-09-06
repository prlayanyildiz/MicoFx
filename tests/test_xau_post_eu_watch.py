"""xau_post_eu_watch — heightened alert after EU re-enable."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.xau_post_eu_watch import active, arm, maybe_alert


def test_arm_and_active(tmp_path, monkeypatch):
    st = tmp_path / "post.json"
    monkeypatch.setattr("scripts.xau_post_eu_watch.STATE_PATH", st)
    now = time.time()
    arm(now_ts=now, autopsy_n=10)
    assert active(now_ts=now)
    assert not active(now_ts=now + 4 * 3600)


def test_alerts_new_loser_once(tmp_path, monkeypatch):
    st = tmp_path / "post.json"
    monkeypatch.setattr("scripts.xau_post_eu_watch.STATE_PATH", st)
    now = 1_000_000.0
    arm(now_ts=now)
    rows = [{
        "symbol": "XAUUSD",
        "ticket": 42,
        "r_realised": -1.0,
        "profit": -3.0,
        "exit_time": now + 60,
    }]
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    a1 = maybe_alert(
        rows, now_ts=now + 120, state_path=st,
        wake_path=wake, cursor_inbox=inbox)
    a2 = maybe_alert(
        rows, now_ts=now + 180, state_path=st,
        wake_path=wake, cursor_inbox=inbox)
    assert a1 and not a2
    assert "POST-EU" in inbox.read_text(encoding="utf-8")


def test_arm_seeds_known_tickets_skips_clock_skew(tmp_path, monkeypatch):
    """Pre-arm XAU losers must not alert even if exit_time > reenabled_at.

    Autopsy exit_time can sit hours ahead of OS time.time(); seeding known
    tickets at arm is the durable gate (04.09 #324704274 false wake).
    """
    st = tmp_path / "post.json"
    monkeypatch.setattr("scripts.xau_post_eu_watch.STATE_PATH", st)
    now = 1_000_000.0
    known = [{
        "symbol": "XAUUSD",
        "ticket": 324704274,
        "r_realised": -1.01,
        "profit": -3.99,
        "exit_time": now + 1300,  # looks "after" arm on a skewed clock
    }]
    arm(now_ts=now, seed_rows=known)
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    assert not maybe_alert(
        known, now_ts=now + 60, state_path=st,
        wake_path=wake, cursor_inbox=inbox)
    assert not inbox.is_file()
    fresh = known + [{
        "symbol": "XAUUSD",
        "ticket": 99,
        "r_realised": -1.0,
        "profit": -2.0,
        "exit_time": now + 200,
    }]
    assert maybe_alert(
        fresh, now_ts=now + 300, state_path=st,
        wake_path=wake, cursor_inbox=inbox)
    assert "#99" in inbox.read_text(encoding="utf-8")
