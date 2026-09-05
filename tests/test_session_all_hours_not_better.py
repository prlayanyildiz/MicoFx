"""Session clocks: all-hours must not beat live NAS/US30/Brent (Claude 07:50)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.bar_snapshot import snapshot_path
from micofx.optimizer import _sessions_key
from scripts.session_exec import _score_windows

# Live clocks from the book (Claude 07:50 table).
_CASES = (
    ("NAS100", "M30", "burst", [{"start": "15:00", "end": "21:00"}]),
    ("US30", "M30", "channel_break", [{"start": "08:00", "end": "16:00"}]),
    ("SpotBrent", "M30", "mtf_pullback", [{"start": "14:00", "end": "22:00"}]),
)


@pytest.mark.parametrize("symbol,tf,strat,live_sess", _CASES)
def test_all_hours_does_not_beat_live_session(symbol, tf, strat, live_sess):
    path = snapshot_path(symbol, tf)
    if not path.exists():
        pytest.skip(f"no {symbol}/{tf} snapshot")
    row = {
        "symbol": symbol,
        "timeframe": tf,
        "strategy": strat,
        "sessions": live_sess,
        "use_sessions": True,
    }
    all_h = [{"start": "00:00", "end": "23:59"}]
    scored = _score_windows(row, [live_sess, all_h])
    by = {_sessions_key(w): h for w, h in scored if isinstance(h, dict)}
    live_k = _sessions_key(live_sess)
    all_k = _sessions_key(all_h)
    if live_k not in by or all_k not in by:
        pytest.skip("incomplete charged scores")
    live_r = float(by[live_k].get("net_r") or 0)
    all_r = float(by[all_k].get("net_r") or 0)
    assert live_r >= all_r - 1.0, (
        f"{symbol}: live session {live_r} should beat/match all-hours {all_r}")
