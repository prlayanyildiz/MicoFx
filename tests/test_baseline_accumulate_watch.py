"""baseline_accumulate_watch — one tick wiring."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.baseline_accumulate_watch import once


def test_once_logs_without_alert(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.panel_ok",
        lambda *a, **k: True,
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.panel_alert",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.silence_snapshot",
        lambda *a, **k: {
            "fire": False, "minutes_open": 0, "signals": {},
        },
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.silence_alert",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.fetch_autopsy_rows",
        lambda *a, **k: [{"symbol": "X"}] * 333,
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.baseline_status",
        lambda n: {
            "armed": True, "new_trades": 0, "target": 25,
            "suppressed": True, "autopsy_n": n,
        },
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.maybe_alert_baseline_ready",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.maybe_alert_first_new_close",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.us30_snapshot",
        lambda *a, **k: {
            "fill_rate": 0.0, "signals": 0, "opened": 0, "poor_fill": False,
        },
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.us30_alert",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.xau_temp_reenable",
        lambda *a, **k: (True, "XAU disable bekliyor (broker_h=6, eu>=8)"),
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.bleed_snapshot",
        lambda *a, **k: {
            "fire": False, "dominant": "", "dominant_share": 0,
            "total_r": 0, "dominant_streak": 0, "armed_auto_a": False,
        },
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.bleed_alert",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.consecutive_non_winners",
        lambda *a, **k: {"streak": 0},
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.fetch_enabled_symbols",
        lambda *a, **k: ["BTCUSD"],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.scan_book",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.alert_book",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.post_eu_alert",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.post_eu_active",
        lambda *a, **k: False,
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.eu_open_brief",
        lambda *a, **k: [],
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.xau_broker_hour",
        lambda *a, **k: 6,
    )
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.xau_session",
        lambda *a, **k: object(),
    )
    with patch("scripts.baseline_accumulate_watch.LOG", tmp_path / "t.log"):
        ready, us30, xau_on, bh = once()
    assert ready is False and us30 is False and xau_on is False
    assert bh == 6
    assert (tmp_path / "t.log").is_file()
    log = (tmp_path / "t.log").read_text(encoding="utf-8")
    assert "baseline_suppress" in log or "suppress=True" in log


def test_bleed_alert_skipped_while_baseline_suppressed(tmp_path, monkeypatch):
    """Post-restart baseline: log bleed fire but do not wake (streak door)."""
    called = {"n": 0}

    def _alert(*a, **k):
        called["n"] += 1
        return ["SHOULD_NOT"]

    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.panel_ok", lambda *a, **k: True)
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.panel_alert", lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.silence_snapshot",
        lambda *a, **k: {"fire": False, "minutes_open": 0, "signals": {}})
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.silence_alert", lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.cb_path_snapshot",
        lambda *a, **k: {"fire": False, "hits": [], "deltas": {}})
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.cb_path_alert", lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.fetch_autopsy_rows",
        lambda *a, **k: [{"symbol": "XAUUSD"}] * 334)
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.baseline_status",
        lambda n: {
            "armed": True, "new_trades": 1, "target": 25,
            "suppressed": True, "autopsy_n": n,
        })
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.maybe_alert_baseline_ready",
        lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.maybe_alert_first_new_close",
        lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.us30_snapshot",
        lambda *a, **k: {
            "fill_rate": 0.0, "signals": 0, "opened": 0, "poor_fill": False,
            "min_signals": 8, "actionable_signals": 0,
        })
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.us30_alert", lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.xau_temp_reenable",
        lambda *a, **k: (False, "ok"))
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.bleed_snapshot",
        lambda *a, **k: {
            "fire": True, "dominant": "XAUUSD", "loss_share": 0.5,
            "streak_r": -6.0, "dominant_streak": 7, "sole_recent": False,
            "armed_auto_a": False,
        })
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.bleed_alert", _alert)
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.consecutive_non_winners",
        lambda *a, **k: {"streak": 7})
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.fetch_enabled_symbols",
        lambda *a, **k: ["XAUUSD"])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.scan_book", lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.alert_book", lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.post_eu_alert", lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.post_eu_active", lambda *a, **k: False)
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.eu_open_brief", lambda *a, **k: [])
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.xau_broker_hour", lambda *a, **k: 10)
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.xau_session", lambda *a, **k: object())
    with patch("scripts.baseline_accumulate_watch.LOG", tmp_path / "t.log"):
        once()
    assert called["n"] == 0
    assert "bleed wakes SUSPEND" in (tmp_path / "t.log").read_text(encoding="utf-8")


def test_sleep_short_while_flag(tmp_path, monkeypatch):
    from scripts.baseline_accumulate_watch import _sleep_sec

    flag = tmp_path / "XAU_TEMP_DISABLE_UNTIL_EU"
    flag.write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.XAU_TEMP_FLAG", flag)
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.post_eu_active",
        lambda: False)
    assert _sleep_sec(900) == 60
    flag.unlink()
    assert _sleep_sec(900) == 900


def test_sleep_short_while_post_eu(tmp_path, monkeypatch):
    from scripts.baseline_accumulate_watch import _sleep_sec

    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.XAU_TEMP_FLAG",
        tmp_path / "missing")
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.post_eu_active",
        lambda: True)
    assert _sleep_sec(900) == 60


def test_sleep_short_session_open(tmp_path, monkeypatch):
    from scripts.baseline_accumulate_watch import _sleep_sec

    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.XAU_TEMP_FLAG",
        tmp_path / "missing")
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.post_eu_active",
        lambda: False)
    assert _sleep_sec(900, broker_h=8) == 60
    assert _sleep_sec(900, broker_h=7) == 900
    assert _sleep_sec(900, broker_h=15) == 60
    assert _sleep_sec(900, broker_h=14) == 900


def test_reload_flag_consumes(tmp_path, monkeypatch):
    from scripts.baseline_accumulate_watch import _reload_requested

    flag = tmp_path / "BASELINE_WATCH_RELOAD"
    flag.write_text("1", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.RELOAD_FLAG", flag)
    assert _reload_requested() is True
    assert not flag.exists()
    assert _reload_requested() is False
def test_heartbeat_stale_alerts_once(tmp_path, monkeypatch):
    from datetime import datetime, timedelta

    from scripts.baseline_accumulate_watch import (
        heartbeat_age_sec,
        maybe_alert_stale_heartbeat,
    )

    hb = tmp_path / "HB"
    hb.write_text(
        (datetime.now() - timedelta(seconds=1300)).isoformat(timespec="seconds"),
        encoding="utf-8")
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.HEARTBEAT", hb)
    assert heartbeat_age_sec() >= 1200
    state = tmp_path / "stale.json"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    first = maybe_alert_stale_heartbeat(
        max_age_sec=1200, state_path=state, wake_path=wake, cursor_inbox=inbox)
    assert first and wake.is_file()
    assert "HEARTBEAT STALE" in inbox.read_text(encoding="utf-8")
    assert maybe_alert_stale_heartbeat(
        max_age_sec=1200, state_path=state, wake_path=wake, cursor_inbox=inbox) == []


def test_heartbeat_fresh_no_alert(tmp_path, monkeypatch):
    from datetime import datetime

    from scripts.baseline_accumulate_watch import maybe_alert_stale_heartbeat

    hb = tmp_path / "HB"
    hb.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    monkeypatch.setattr(
        "scripts.baseline_accumulate_watch.HEARTBEAT", hb)
    assert maybe_alert_stale_heartbeat(
        max_age_sec=1200,
        state_path=tmp_path / "s.json",
        wake_path=tmp_path / "W.txt",
        cursor_inbox=tmp_path / "I.md",
    ) == []
