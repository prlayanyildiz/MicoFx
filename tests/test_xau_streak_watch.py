"""xau_streak_watch — consecutive non-winner count + alert dedupe."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.xau_streak_watch import (
    alert_streak,
    consecutive_non_winners,
    is_winner,
    should_alert,
)


def _row(symbol: str, r: float, ticket: int = 1) -> dict:
    return {
        "symbol": symbol,
        "r_realised": r,
        "exit_reason": "sl" if r <= 0 else "trail",
        "mfe_r": abs(r),
        "ticket": ticket,
        "exit_time": ticket,
    }


def test_is_winner():
    assert is_winner({"r_realised": 0.1})
    assert not is_winner({"r_realised": 0.0})
    assert not is_winner({"r_realised": -1.0})


def test_scan_book_and_alert_non_xau(tmp_path):
    from scripts.xau_streak_watch import alert_book, scan_book

    rows = (
        [_row("NAS100", 1.0, 0)]
        + [_row("NAS100", -1.0, i) for i in range(1, 6)]
        + [_row("XAUUSD", 1.0, 10)]
        + [_row("XAUUSD", -0.1, i) for i in range(11, 14)]
    )
    reps = scan_book(rows, ["NAS100", "XAUUSD"])
    by = {r["symbol"]: r for r in reps}
    assert by["NAS100"]["level"] == "review"
    assert by["XAUUSD"]["level"] == "watch"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    state = tmp_path / "book.json"
    notes = alert_book(
        reps, wake_path=wake, cursor_inbox=inbox, state_path=state)
    assert any("NAS100" in n or "wake" in n for n in notes)
    assert "NAS100" in inbox.read_text(encoding="utf-8")
    # second call dedupes
    assert alert_book(
        reps, wake_path=wake, cursor_inbox=inbox, state_path=state) == []


def test_recent_expectancy_alerts_below_threshold():
    from scripts.xau_streak_watch import recent_expectancy

    rows = [_row("XAUUSD", -0.5, i) for i in range(10)]
    exp = recent_expectancy(rows, n=10)
    assert exp["alert"] is True
    assert exp["expectancy_r"] <= -0.3
    rows2 = [_row("XAUUSD", 0.5, i) for i in range(10)]
    assert recent_expectancy(rows2, n=10)["alert"] is False


def test_streak_stops_at_last_winner():
    rows = [
        _row("XAUUSD", 2.0, 1),
        _row("XAUUSD", -1.0, 2),
        _row("NAS100", -1.0, 3),
        _row("XAUUSD", -0.05, 4),
        _row("XAUUSD", -1.03, 5),
    ]
    out = consecutive_non_winners(rows)
    assert out["streak"] == 3
    assert out["level"] == "watch"
    assert len(out["tail"]) == 3


def test_review_and_escalate_levels():
    five = [_row("XAUUSD", 1.0, 0)] + [
        _row("XAUUSD", -1.0, i) for i in range(1, 6)
    ]
    assert consecutive_non_winners(five)["level"] == "review"
    eight = [_row("XAUUSD", 1.0, 0)] + [
        _row("XAUUSD", -0.1, i) for i in range(1, 9)
    ]
    assert consecutive_non_winners(eight)["level"] == "escalate"


def test_alert_dedupes_same_level(tmp_path):
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    state = tmp_path / "state.json"
    inbox.write_text("# old\n", encoding="utf-8")
    report = consecutive_non_winners(
        [_row("XAUUSD", 1.0, 0)] + [_row("XAUUSD", -1.0, i) for i in range(1, 6)]
    )
    assert should_alert(report, {}) is True
    first = alert_streak(
        report, wake_path=wake, cursor_inbox=inbox, state_path=state,
        run_hybrid_review=False)
    assert wake.is_file() and "STREAK REVIEW" in inbox.read_text(encoding="utf-8")
    assert first
    second = alert_streak(
        report, wake_path=wake, cursor_inbox=inbox, state_path=state,
        run_hybrid_review=False)
    assert second == []


def test_escalate_realerts_after_review(tmp_path):
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    state = tmp_path / "state.json"
    review = consecutive_non_winners(
        [_row("XAUUSD", 1.0, 0)] + [_row("XAUUSD", -1.0, i) for i in range(1, 6)]
    )
    alert_streak(
        review, wake_path=wake, cursor_inbox=inbox, state_path=state,
        run_hybrid_review=False)
    esc = consecutive_non_winners(
        [_row("XAUUSD", 1.0, 0)] + [_row("XAUUSD", -1.0, i) for i in range(1, 9)]
    )
    assert should_alert(esc, {"alerted_level": "review"}) is True
    lines = alert_streak(
        esc, wake_path=wake, cursor_inbox=inbox, state_path=state,
        run_hybrid_review=False)
    assert any("escalate" in x for x in lines)
    assert "ESCALATE" in inbox.read_text(encoding="utf-8")


def test_post_restart_baseline_suppresses_alerts(tmp_path):
    """Claude 05:20: pre-restart book-exp invalid until N new trades."""
    import json

    from scripts.xau_streak_watch import (
        alert_book,
        alerts_suppressed_by_baseline,
        baseline_status,
        maybe_alert_baseline_ready,
        scan_book,
    )

    base = tmp_path / "POST_RESTART_BASELINE.json"
    base.write_text(json.dumps({
        "autopsy_n_at_stamp": 100,
        "target_new_trades": 25,
        "restart_at": "2026-09-04T05:22:16",
    }), encoding="utf-8")
    suppressed, note = alerts_suppressed_by_baseline(105, baseline_path=base)
    assert suppressed is True
    assert "5/25" in note
    ok, _ = alerts_suppressed_by_baseline(130, baseline_path=base)
    assert ok is False

    st = baseline_status(105, baseline_path=base)
    assert st["armed"] and st["new_trades"] == 5 and st["suppressed"]

    rows = [_row("NAS100", 1.0, 0)] + [_row("NAS100", -1.0, i) for i in range(1, 6)]
    reps = scan_book(rows, ["NAS100"])
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    state = tmp_path / "book.json"
    notes = alert_book(
        reps, wake_path=wake, cursor_inbox=inbox, state_path=state,
        baseline_path=base, autopsy_n=105)
    assert notes and any("baseline" in n for n in notes)
    assert not wake.exists()
    assert not inbox.exists() or "NAS100" not in inbox.read_text(encoding="utf-8")

    assert maybe_alert_baseline_ready(
        105, baseline_path=base, wake_path=wake, cursor_inbox=inbox) == []
    fired = maybe_alert_baseline_ready(
        130, baseline_path=base, wake_path=wake, cursor_inbox=inbox)
    assert fired and wake.is_file()
    assert "BASELINE READY" in inbox.read_text(encoding="utf-8")
    assert maybe_alert_baseline_ready(
        130, baseline_path=base, wake_path=wake, cursor_inbox=inbox) == []


def test_first_new_close_alerts_once(tmp_path):
    import json

    from scripts.xau_streak_watch import maybe_alert_first_new_close

    base = tmp_path / "POST_RESTART_BASELINE.json"
    base.write_text(json.dumps({
        "autopsy_n_at_stamp": 100,
        "target_new_trades": 25,
        "restart_at": "2026-09-04T05:22:16",
    }), encoding="utf-8")
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    assert maybe_alert_first_new_close(
        100, baseline_path=base, wake_path=wake, cursor_inbox=inbox) == []
    fired = maybe_alert_first_new_close(
        101, baseline_path=base, wake_path=wake, cursor_inbox=inbox)
    assert fired and "FIRST POST-RESTART CLOSE" in inbox.read_text(encoding="utf-8")
    assert maybe_alert_first_new_close(
        105, baseline_path=base, wake_path=wake, cursor_inbox=inbox) == []
