"""night_bleed_guard — 24h dominant-bleed detection."""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.night_bleed_guard import maybe_alert, snapshot


def _row(sym: str, r: float, age_h: float, now: float) -> dict:
    return {
        "symbol": sym,
        "r_realised": r,
        "profit": r * 3.0,
        "exit_time": now - age_h * 3600,
    }


def test_snapshot_fires_despite_earlier_winner():
    """Claude 05:58 pattern: +3R then seven losers — net share diluted."""
    now = time.time()
    rows = [_row("XAUUSD", 3.0, 20, now)]
    for i in range(7):
        rows.append(_row("XAUUSD", -1.0, 1 + i, now))
    rows.append(_row("NAS100", -0.5, 8, now))
    snap = snapshot(rows, now_ts=now, streaks={"XAUUSD": 7, "NAS100": 1})
    assert snap["fire"] is True
    assert snap["dominant"] == "XAUUSD"
    assert snap["streak_r"] <= -5.0
    assert snap["loss_share"] >= 0.50


def test_snapshot_quiet_when_mixed_equal_losses():
    now = time.time()
    rows = [
        _row("XAUUSD", -2.0, 1, now),
        _row("NAS100", -2.0, 2, now),
        _row("GER40", -2.0, 3, now),
    ]
    snap = snapshot(rows, now_ts=now, streaks={"XAUUSD": 8})
    assert snap["fire"] is False


def test_sole_recent_trader_fires():
    now = time.time()
    rows = [_row("XAUUSD", -1.0, h, now) for h in range(1, 8)]
    snap = snapshot(rows, now_ts=now)
    assert snap["sole_recent"] is True
    assert snap["fire"] is True


def test_maybe_alert_dedupes(tmp_path):
    snap = {
        "fire": True,
        "dominant": "XAUUSD",
        "dominant_share": 0.3,
        "loss_share": 0.7,
        "dominant_streak": 7,
        "streak_r": -7.0,
        "total_r": -7.5,
        "window_h": 24,
        "by_symbol": {"XAUUSD": {"n": 7, "r": -7.0, "profit": -20.0}},
        "armed_auto_a": False,
    }
    state = tmp_path / "st.json"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    a1 = maybe_alert(snap, state_path=state, wake_path=wake, cursor_inbox=inbox)
    a2 = maybe_alert(snap, state_path=state, wake_path=wake, cursor_inbox=inbox)
    assert a1 and not a2
    assert wake.is_file() and "NIGHT BLEED" in inbox.read_text(encoding="utf-8")


def test_apply_a_vetoed_without_force(tmp_path, monkeypatch):
    import scripts.night_bleed_guard as nb
    from scripts.night_bleed_guard import maybe_apply_a

    arm = tmp_path / "AUTO_NIGHT_BLEED_A"
    arm.write_text("x", encoding="utf-8")
    monkeypatch.setattr(nb, "ARM_PATH", arm)
    monkeypatch.setattr(nb, "FORCE_PATH", tmp_path / "missing_force")
    ok, msg = maybe_apply_a({"fire": True, "dominant": "XAUUSD"})
    assert ok and "vetoed" in msg.lower()
