"""Spread widen helpers and gates_only apply."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.spread_exec import apply_spread_widen, best_widen_run


def test_best_widen_run_picks_higher_cap_with_holdout():
    history = [
        {"id": 1, "strategy": "channel_break", "validated": True,
         "holdout": {"net_r": 40}, "params": {"max_spread_atr": 0.05}},
        {"id": 2, "strategy": "burst", "validated": True,
         "holdout": {"net_r": 31}, "params": {"max_spread_atr": 0.18}},
    ]
    row = best_widen_run(history, 0.05)
    assert row is not None
    # Higher holdout wins even at a smaller widen; id1 is not wider than 0.05.
    assert row["id"] == 2
    assert row["params"]["max_spread_atr"] == 0.18


def test_best_widen_run_prefers_better_hold_then_modest_cap():
    """US30: 0.10 +29.8R should beat 0.12 +22R history row."""
    history = [
        {"id": 10, "strategy": "channel_break", "validated": True,
         "holdout": {"net_r": 22.26}, "params": {"max_spread_atr": 0.12}},
        {"id": 11, "strategy": "channel_break", "validated": True,
         "holdout": {"net_r": 29.8}, "params": {"max_spread_atr": 0.10}},
        {"id": 12, "strategy": "channel_break", "validated": True,
         "holdout": {"net_r": 29.8}, "params": {"max_spread_atr": 0.11}},
    ]
    row = best_widen_run(history, 0.08)
    assert row is not None
    assert row["id"] == 11
    assert row["params"]["max_spread_atr"] == 0.10


def test_best_widen_run_respects_live_family():
    """SpotBrent mtf must not widen from a burst +68R history stamp."""
    history = [
        {"id": 1, "strategy": "burst", "validated": True,
         "holdout": {"net_r": 68.0}, "params": {"max_spread_atr": 0.18}},
        {"id": 2, "strategy": "mtf_pullback", "validated": True,
         "holdout": {"net_r": 24.0}, "params": {"max_spread_atr": 0.12}},
    ]
    row = best_widen_run(history, 0.05, strategy="mtf_pullback")
    assert row is not None
    assert row["id"] == 2
    assert best_widen_run(history, 0.05, strategy="channel_break") is None


def test_best_widen_run_skips_when_no_wider_cap():
    history = [
        {"id": 1, "strategy": "channel_break", "validated": True,
         "holdout": {"net_r": 40}, "params": {"max_spread_atr": 0.05}},
    ]
    assert best_widen_run(history, 0.05) is None


def test_apply_spread_widen_refuses_six_slice_erosion():
    history = [
        {"id": 9, "strategy": "mtf_pullback", "validated": True,
         "holdout": {"net_r": 80.0}, "params": {"max_spread_atr": 0.08}},
    ]
    live = {
        "symbol": "SpotBrent", "strategy": "mtf_pullback",
        "timeframe": "M30", "max_spread_atr": 0.05,
        "opt_summary": {"holdout": {"net_r": 40.0}},
        "use_sessions": True,
        "sessions": [{"start": "14:00", "end": "22:00"}],
    }

    def fake_slices(row, field=None, value=None, **kw):
        if value is None or abs(float(value) - 0.05) < 1e-9:
            return [0.0, -1.9, 11.7, 5.1, -6.6, 41.5]
        return [0.0, -8.3, -25.1, -3.8, -27.8, 81.0]

    with patch("scripts.exec_gates.pipeline_frozen", return_value=False):
        with patch("scripts.spread_exec._live_symbol_row", return_value=live):
            with patch("scripts.exec_gates.charged_slice_nets", fake_slices):
                with patch("urllib.request.urlopen") as post:
                    ok, msg = apply_spread_widen(
                        {}, panel="http://127.0.0.1:8900", symbol="SpotBrent",
                        current_cap=0.05, history=history,
                        strategy="mtf_pullback")
    assert ok
    assert "6-slice erozyon" in msg
    post.assert_not_called()


def test_apply_spread_widen_skips_when_pipeline_frozen():
    ok, msg = apply_spread_widen(
        {}, panel="http://127.0.0.1:8900", symbol="US30",
        current_cap=0.08, history=[])
    assert ok
    assert "FREEZE" in msg
