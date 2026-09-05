"""Fail first: session pick must beat live charged net_r by margin."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.session_exec import best_session_upgrade, live_trade_sessions


def test_live_trade_sessions_respects_use_sessions_false():
    """JPN225: leftover 23-08 on disk is unread when use_sessions=False."""
    assert live_trade_sessions({
        "use_sessions": False,
        "sessions": [{"start": "23:00", "end": "08:00"}],
    }) == [{"start": "00:00", "end": "23:59"}]


def test_best_session_upgrade_requires_delta():
    scored = [
        ([{"start": "13:00", "end": "21:00"}],
         {"net_r": 22.8, "profit_factor": 1.17, "trades": 215, "max_dd_r": 22.4}),
        ([{"start": "14:00", "end": "22:00"}],
         {"net_r": 32.0, "profit_factor": 1.23, "trades": 222, "max_dd_r": 24.4}),
        ([{"start": "15:00", "end": "21:00"}],
         {"net_r": 23.7, "profit_factor": 1.20, "trades": 193, "max_dd_r": 23.2}),
    ]
    live = [{"start": "13:00", "end": "21:00"}]
    pick = best_session_upgrade(live, scored, min_delta_r=5.0)
    assert pick is not None
    assert pick["sessions"] == [{"start": "14:00", "end": "22:00"}]
    assert pick["net_r"] == 32.0


def test_best_session_upgrade_skips_small_gain():
    scored = [
        ([{"start": "15:00", "end": "21:00"}],
         {"net_r": 103.8, "profit_factor": 1.27, "trades": 559}),
        ([{"start": "14:00", "end": "22:00"}],
         {"net_r": 104.8, "profit_factor": 1.24, "trades": 624}),
    ]
    live = [{"start": "15:00", "end": "21:00"}]
    assert best_session_upgrade(live, scored, min_delta_r=5.0) is None


def test_best_session_upgrade_rejects_pf_collapse():
    scored = [
        ([{"start": "08:00", "end": "16:00"}],
         {"net_r": 30.0, "profit_factor": 1.30, "trades": 200}),
        ([{"start": "00:00", "end": "23:59"}],
         {"net_r": 50.0, "profit_factor": 1.05, "trades": 500}),
    ]
    live = [{"start": "08:00", "end": "16:00"}]
    assert best_session_upgrade(live, scored, min_delta_r=5.0) is None
