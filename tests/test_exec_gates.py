"""6-slice robustness gate rejects last-segment-only overfit (JPN pattern)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.exec_gates as eg
from scripts.exec_gates import gate_pick, robust_enough, upgrade_robust


def test_gate_pick_rejects_fragile_challenger():
    row = {"symbol": "JPN225", "timeframe": "M30"}
    pick = {"trail_step_atr": 3.6, "net_r": 158.0}

    def fake_report(row, field=None, value=None, parts=6):
        if field is None:
            return {
                "nets": [9.0, 16.0, 9.0, 26.0, 68.0, 54.0],
                "valid": [True] * 6,
            }
        return {
            "nets": [-17.0, -5.0, 0.0, -3.0, 12.0, 151.0],
            "valid": [True] * 6,
        }

    with patch.object(eg, "EXEC_PIPELINE_FROZEN", False):
        with patch.object(eg, "pipeline_frozen", return_value=False):
            with patch("scripts.exec_gates.charged_slice_report", side_effect=fake_report):
                assert gate_pick(row, pick, field="trail_step_atr",
                                 value_key="trail_step_atr") is None


def test_gate_pick_keeps_robust_challenger():
    row = {"symbol": "GER40", "timeframe": "M30"}
    pick = {"atr_pct_min": 0.2, "net_r": 82.0}
    live = [9.0, 16.0, 9.0, 26.0, 60.0, 50.0]
    chal = [9.0, 16.0, 9.0, 26.0, 68.0, 54.0]  # +17 full, same wins, mild backload

    def fake_report(row, field=None, value=None, parts=6):
        nets = live if field is None else chal
        return {"nets": nets, "valid": [True] * 6}

    with patch.object(eg, "EXEC_PIPELINE_FROZEN", False):
        with patch.object(eg, "pipeline_frozen", return_value=False):
            with patch("scripts.exec_gates.charged_slice_report", side_effect=fake_report):
                out = gate_pick(row, pick, field="atr_pct_min", value_key="atr_pct_min")
    assert out is pick


def test_gate_pick_frozen_always_none():
    row = {"symbol": "GER40", "timeframe": "M30"}
    pick = {"atr_pct_min": 0.2, "net_r": 82.0}
    with patch.object(eg, "EXEC_PIPELINE_FROZEN", True):
        assert gate_pick(row, pick, field="atr_pct_min",
                         value_key="atr_pct_min") is None
    with patch.object(eg, "EXEC_PIPELINE_FROZEN", False):
        with patch.object(eg, "pipeline_frozen", return_value=True):
            assert gate_pick(row, pick, field="atr_pct_min",
                             value_key="atr_pct_min") is None


def test_upgrade_robust_rejects_win_regression():
    live = [9.0, 16.0, 9.0, 26.0, 68.0, 54.0]  # 6/6
    chal = [15.0, 13.0, -2.0, 23.0, 72.0, 63.0]  # 5/6, full same-ish
    assert upgrade_robust(live, chal) is False


def test_upgrade_robust_rejects_backload_spike():
    # Same wins + big full gain, but last-2 share jumps >15pp.
    live = [50.0, 50.0, 50.0, 50.0, 40.0, 40.0]  # share 80/280 ≈ 0.29
    chal = [40.0, 40.0, 40.0, 40.0, 90.0, 110.0]  # share 200/360 ≈ 0.56
    assert upgrade_robust(live, chal) is False


def test_upgrade_robust_rejects_deeper_min_slice():
    # Same wins + full +5R, but worst slice digs deeper (Claude 03:50).
    live = [10.0, -5.0, 10.0, 10.0, 10.0, 10.0]  # 5/6, min=-5, sum=45
    chal = [12.0, -12.0, 12.0, 12.0, 12.0, 12.0]  # 5/6, min=-12, sum=48
    assert upgrade_robust(live, chal) is False


def test_upgrade_robust_rejects_insufficient_full_delta():
    live = [9.0, 16.0, 9.0, 26.0, 68.0, 54.0]
    chal = [9.0, 16.0, 9.0, 26.0, 69.0, 54.0]  # +1R only
    assert upgrade_robust(live, chal) is False


def test_robust_enough_counts_positive_slices():
    row = {"symbol": "X"}

    with patch(
        "scripts.exec_gates.charged_slice_report",
        return_value={
            "nets": [-17.0, -5.0, 0.0, -3.0, 12.0, 151.0],
            "valid": [True] * 6,
            "valid_n": 6,
            "wins_valid": 2,
        },
    ):
        assert robust_enough(row) is False  # 2/6
    with patch(
        "scripts.exec_gates.charged_slice_report",
        return_value={
            "nets": [9.0, 16.0, 9.0, 26.0, 68.0, 54.0],
            "valid": [True] * 6,
            "valid_n": 6,
            "wins_valid": 6,
        },
    ):
        assert robust_enough(row) is True


def test_slice_quality_rejects_imputed_and_sparse():
    assert eg.slice_quality_ok(
        spread_missing_ratio=0.0, bars_per_day=40.0,
        median_bars_per_day=40.0, trades=20) is True
    assert eg.slice_quality_ok(
        spread_missing_ratio=1.0, bars_per_day=40.0,
        median_bars_per_day=40.0, trades=20) is False
    assert eg.slice_quality_ok(
        spread_missing_ratio=0.0, bars_per_day=5.5,
        median_bars_per_day=43.0, trades=75) is False
    assert eg.slice_quality_ok(
        spread_missing_ratio=0.0, bars_per_day=40.0,
        median_bars_per_day=40.0, trades=10) is False


def test_upgrade_robust_ignores_invalid_slice_wins():
    """GER40-shaped: dirty head must not invent wins (Claude 15:24)."""
    live = [25.0, 20.0, 20.0, 30.0, 30.0, 30.0]
    chal = [40.0, 22.0, 22.0, 32.0, 32.0, 32.0]
    assert upgrade_robust(live, chal) is True
    valid = [False, True, True, True, True, True]
    assert upgrade_robust(live, chal, live_valid=valid, chal_valid=valid) is True
    thin = [False, False, False, True, True, True]
    assert upgrade_robust(live, chal, live_valid=thin, chal_valid=thin) is False
