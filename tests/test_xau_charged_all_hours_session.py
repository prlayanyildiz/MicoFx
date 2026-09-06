"""XAU charged session windows — all-hours must stay best (Claude 07:10 retract)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.bar_snapshot import snapshot_path
from micofx.optimizer import SEARCH_SESSION_WINDOWS, _sessions_key
from scripts.session_exec import _score_windows, live_trade_sessions


def test_xau_charged_all_hours_beats_day_windows():
    """Night session-cut would crush charged edge (+250 vs +24 day)."""
    path = snapshot_path("XAUUSD", "M15")
    if not path.exists():
        pytest.skip("no XAUUSD/M15 holdout snapshot")
    row = {
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "strategy": "mtf_pullback",
        "sessions": [{"start": "00:00", "end": "23:59"}],
        "use_sessions": True,
        "sl_atr_mult": 0.7,
        "trail_start_atr": 1.5,
        "trail_step_atr": 2.5,
        "breakeven_at_r": 1.5,
    }
    live = live_trade_sessions(row)
    windows = list(SEARCH_SESSION_WINDOWS)
    if _sessions_key(live) not in {_sessions_key(w) for w in windows}:
        windows = [live, *windows]
    scored = _score_windows(row, windows)
    assert scored, "expected charged scores"
    nets = []
    for w, hold in scored:
        if not isinstance(hold, dict) or hold.get("net_r") is None:
            continue
        nets.append((_sessions_key(w), float(hold["net_r"])))
    assert nets
    best_key, best_net = max(nets, key=lambda t: t[1])
    all_hours = _sessions_key([{"start": "00:00", "end": "23:59"}])
    assert best_key == all_hours, (
        f"expected all-hours best, got {best_key} @ {best_net}; full={nets}")
    day_key = _sessions_key([{"start": "08:00", "end": "16:00"}])
    day = next((n for k, n in nets if k == day_key), None)
    if day is not None:
        assert best_net > day + 50, "all-hours should crush 08-16 day window"
