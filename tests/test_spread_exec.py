"""Spread widen helpers and gates_only apply."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.spread_exec import best_widen_run


def test_best_widen_run_picks_higher_cap_with_holdout():
    history = [
        {"id": 1, "strategy": "channel_break", "validated": True,
         "holdout": {"net_r": 40}, "params": {"max_spread_atr": 0.05}},
        {"id": 2, "strategy": "burst", "validated": True,
         "holdout": {"net_r": 31}, "params": {"max_spread_atr": 0.18}},
    ]
    row = best_widen_run(history, 0.05)
    assert row is not None
    assert row["id"] == 2
    assert row["params"]["max_spread_atr"] == 0.18


def test_best_widen_run_skips_when_no_wider_cap():
    history = [
        {"id": 1, "strategy": "channel_break", "validated": True,
         "holdout": {"net_r": 40}, "params": {"max_spread_atr": 0.05}},
    ]
    assert best_widen_run(history, 0.05) is None
