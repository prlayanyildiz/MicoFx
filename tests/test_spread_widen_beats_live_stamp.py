"""Fail first: widen must not regress a tighter live holdout stamp (NAS100)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.spread_exec import best_widen_run


def test_best_widen_run_refuses_weaker_wider_than_live_stamp():
    """NAS100: live 0.05 / +103R must not widen to 0.08 / +99R history."""
    history = [
        {"id": 705, "strategy": "burst", "validated": True,
         "holdout": {"net_r": 103.48}, "params": {"max_spread_atr": 0.05}},
        {"id": 638, "strategy": "burst", "validated": True,
         "holdout": {"net_r": 99.09}, "params": {"max_spread_atr": 0.08}},
    ]
    assert best_widen_run(
        history, 0.05, strategy="burst", live_hold_r=103.48) is None


def test_best_widen_run_allows_wider_that_beats_live_stamp():
    history = [
        {"id": 1, "strategy": "channel_break", "validated": True,
         "holdout": {"net_r": 40.0}, "params": {"max_spread_atr": 0.12}},
    ]
    row = best_widen_run(
        history, 0.08, strategy="channel_break", live_hold_r=25.0)
    assert row is not None
    assert row["id"] == 1
