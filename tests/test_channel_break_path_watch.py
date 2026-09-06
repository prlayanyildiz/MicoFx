"""channel_break_path_watch — signal without fill."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.channel_break_path_watch import ensure_stamp, evaluate, maybe_alert


def test_evaluate_fires_on_signal_zero_open():
    quiet = evaluate(
        broker_h=9,
        deltas={"GER40": {"signals": 0, "opened": 0}, "US30": {"signals": 0, "opened": 0}},
    )
    assert quiet["fire"] is False
    hit = evaluate(
        broker_h=9,
        deltas={"GER40": {"signals": 1, "opened": 0}, "US30": {"signals": 0, "opened": 0}},
        rows={"GER40": {"blocks": {"adx": 1}}},
    )
    assert hit["fire"] is True
    assert hit["hits"][0]["symbol"] == "GER40"
    assert "gated" in hit["hits"][0]["lean"]
    filled = evaluate(
        broker_h=9,
        deltas={"GER40": {"signals": 2, "opened": 1}, "US30": {"signals": 0, "opened": 0}},
    )
    assert filled["fire"] is False


def test_ensure_stamp_delta(tmp_path):
    st = tmp_path / "s.json"
    raw = {
        "GER40": {"signals": 3, "opened": 1},
        "US30": {"signals": 0, "opened": 0},
    }
    d0 = ensure_stamp(raw, in_window=True, day="2026-09-04", state_path=st)
    assert d0["GER40"] == {"signals": 0, "opened": 0}
    raw2 = {
        "GER40": {"signals": 4, "opened": 1},
        "US30": {"signals": 0, "opened": 0},
    }
    d1 = ensure_stamp(raw2, in_window=True, day="2026-09-04", state_path=st)
    assert d1["GER40"] == {"signals": 1, "opened": 0}


def test_maybe_alert_once(tmp_path):
    rep = evaluate(
        broker_h=10,
        deltas={"GER40": {"signals": 1, "opened": 0}, "US30": {"signals": 0, "opened": 0}},
        rows={"GER40": {"blocks": {}}},
    )
    st = tmp_path / "s.json"
    a1 = maybe_alert(
        rep, state_path=st, wake_path=tmp_path / "W.txt", cursor_inbox=tmp_path / "I.md")
    a2 = maybe_alert(
        rep, state_path=st, wake_path=tmp_path / "W.txt", cursor_inbox=tmp_path / "I.md")
    assert a1 and not a2
    assert "CHANNEL_BREAK PATH" in (tmp_path / "I.md").read_text(encoding="utf-8")