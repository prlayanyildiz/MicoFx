"""session_open_silence — per-symbol ~1/mo book silence watch."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.session_open_silence import (
    classify_bar_health,
    ensure_open_stamp,
    evaluate,
    maybe_alert,
    minutes_open_in_session,
    update_session_gaps,
)


def test_evaluate_rejects_p50_same_day_floor():
    """Claude 11:34: 270min = GER40 p50 — must NOT fire on same-day open alone."""
    early = evaluate(broker_h=8, broker_min=30, signals={"GER40": 0, "US30": 0})
    assert early["fire"] is False
    noisy = evaluate(broker_h=12, broker_min=30, signals={"GER40": 1, "US30": 0})
    assert noisy["fire"] is False
    mid = evaluate(broker_h=12, broker_min=30, signals={"GER40": 0, "US30": 0})
    assert mid["fire"] is False and mid["minutes_open"] == 270


def test_evaluate_per_symbol_gap_thresholds():
    """~1 fire/month: GER40 870 / US30 1680 / NAS100 690 session-inside minutes."""
    ger = evaluate(
        broker_h=12, broker_min=0,
        signals={"GER40": 0, "US30": 0},
        gaps={"GER40": 870, "US30": 100},
    )
    assert ger["fire"] is True and "GER40" in ger["fire_syms"]
    us = evaluate(
        broker_h=12, broker_min=0,
        signals={"GER40": 0, "US30": 0},
        gaps={"GER40": 100, "US30": 1680},
    )
    assert us["fire"] is True and "US30" in us["fire_syms"]
    nas = evaluate(
        broker_h=16, broker_min=0,
        signals={"NAS100": 0},
        gaps={"NAS100": 690},
    )
    assert nas["fire"] is True and "NAS100" in nas["fire_syms"]
    short = evaluate(
        broker_h=12, broker_min=0,
        signals={"GER40": 0, "US30": 0},
        gaps={"GER40": 869, "US30": 1679},
    )
    assert short["fire"] is False


def test_wrap_helper_still_computes_overnight():
    """Generic wrap math kept; JPN live watch no longer uses it (13:52)."""
    assert minutes_open_in_session(23, 30, h_lo=23, h_hi=8, wrap=True) == 30
    assert minutes_open_in_session(1, 0, h_lo=23, h_hi=8, wrap=True) == 120
    assert minutes_open_in_session(12, 0, h_lo=23, h_hi=8, wrap=True) is None


def test_jpn_uses_tradable_24h_not_leftover_sessions():
    """JPN225 use_sessions=False → 2520min wall-clock, not 23-08 wrap."""
    from scripts.session_open_silence import BOOK

    thr, lo, hi, wrap = BOOK["JPN225"]
    assert thr == 2520 and lo == 0 and hi == 23 and wrap is False
    # Midday is in-window (unlike leftover 23-08 wrap).
    assert minutes_open_in_session(12, 0, h_lo=lo, h_hi=hi, wrap=wrap) == 12 * 60
    jpn = evaluate(
        broker_h=12, broker_min=0,
        signals={"JPN225": 0},
        gaps={"JPN225": 2520},
    )
    assert jpn["fire"] is True and "JPN225" in jpn["fire_syms"]


def test_update_session_gaps_accumulates_across_days(tmp_path):
    st = tmp_path / "s.json"
    # First sight catch-up to minutes_open.
    g0 = update_session_gaps(
        signals={"GER40": 0, "US30": 0},
        minutes_open_by_sym={"GER40": 480, "US30": 480},
        in_window_by_sym={"GER40": True, "US30": True},
        day="2026-09-04",
        state_path=st,
    )
    assert g0["GER40"] == 480
    # Later same day: only the delta adds.
    g0b = update_session_gaps(
        signals={"GER40": 0, "US30": 0},
        minutes_open_by_sym={"GER40": 500, "US30": 500},
        in_window_by_sym={"GER40": True, "US30": True},
        day="2026-09-04",
        state_path=st,
    )
    assert g0b["GER40"] == 500
    g1 = update_session_gaps(
        signals={"GER40": 0, "US30": 0},
        minutes_open_by_sym={"GER40": 100, "US30": 100},
        in_window_by_sym={"GER40": True, "US30": True},
        day="2026-09-05",
        state_path=st,
    )
    assert g1["GER40"] == 600
    g2 = update_session_gaps(
        signals={"GER40": 1, "US30": 0},
        minutes_open_by_sym={"GER40": 200, "US30": 200},
        in_window_by_sym={"GER40": True, "US30": True},
        day="2026-09-05",
        state_path=st,
    )
    assert g2["GER40"] == 0 and g2["US30"] == 700


def test_maybe_alert_once_per_gap_episode(tmp_path):
    rep = evaluate(
        broker_h=13, broker_min=0,
        signals={"GER40": 0, "US30": 0},
        gaps={"GER40": 870, "US30": 0},
    )
    rep["bar_health"] = {"overall": "ok"}
    st = tmp_path / "s.json"
    wake = tmp_path / "W.txt"
    inbox = tmp_path / "I.md"
    a1 = maybe_alert(rep, state_path=st, wake_path=wake, cursor_inbox=inbox)
    a2 = maybe_alert(rep, state_path=st, wake_path=wake, cursor_inbox=inbox)
    assert a1 and not a2
    text = inbox.read_text(encoding="utf-8")
    assert "SILENCE" in text
    assert "lean=gercek-quiet" in text
    assert "GER40" in text


def test_ensure_open_stamp_delta_not_raw_7d(tmp_path):
    st = tmp_path / "s.json"
    d0 = ensure_open_stamp(
        {"GER40": 5, "US30": 2}, in_window=True, day="2026-09-04",
        state_path=st, symbols=("GER40", "US30"))
    assert d0 == {"GER40": 0, "US30": 0}
    d1 = ensure_open_stamp(
        {"GER40": 5, "US30": 3}, in_window=True, day="2026-09-04",
        state_path=st, symbols=("GER40", "US30"))
    assert d1 == {"GER40": 0, "US30": 1}
    late = evaluate(
        broker_h=12, broker_min=30, signals=d0, gaps={"GER40": 870, "US30": 870})
    assert late["fire"] is True
    d2 = ensure_open_stamp(
        {"GER40": 9, "US30": 3}, in_window=True, day="2026-09-05",
        state_path=st, symbols=("GER40", "US30"))
    assert d2 == {"GER40": 0, "US30": 0}


def test_classify_bar_health_ok_vs_stuck():
    ok = classify_bar_health(
        last_bars={"GER40": 1000, "US30": 1000},
        broker_epoch=1000 + 30 * 60,
    )
    assert ok["overall"] == "ok"
    stuck = classify_bar_health(
        last_bars={"GER40": 1000, "US30": 1000},
        broker_epoch=1000 + 3 * 3600,
    )
    assert stuck["overall"] == "stuck"


def test_fetch_bar_health_uses_timegm_not_mktime():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "session_open_silence.py").read_text(
        encoding="utf-8")
    body = src.split("def fetch_bar_health")[1].split("def maybe_alert")[0]
    assert "calendar.timegm" in body
    assert "_time.mktime" not in body
