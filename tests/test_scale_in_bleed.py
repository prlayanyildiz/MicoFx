"""scale_in_bleed classifier unit tests (no panel / MT5)."""
from __future__ import annotations

from scripts.scale_in_bleed import classify_scale_ins


def test_first_only_no_overlap():
    rows = [
        {"symbol": "GER40", "fill_time": 100, "exit_time": 200, "r_realised": 1.0},
        {"symbol": "GER40", "fill_time": 210, "exit_time": 300, "r_realised": -1.0},
    ]
    rep = classify_scale_ins(rows, symbols=frozenset({"GER40"}))
    g = rep["symbols"]["GER40"]
    assert g["first_n"] == 2
    assert g["scale_n"] == 0
    assert g["live_net_r"] == 0.0


def test_scale_in_overlap_counts_second():
    rows = [
        {"symbol": "NAS100", "fill_time": 100, "exit_time": 300, "r_realised": -1.0},
        {"symbol": "NAS100", "fill_time": 150, "exit_time": 250, "r_realised": -1.0},
        {"symbol": "NAS100", "fill_time": 310, "exit_time": 400, "r_realised": 0.5},
    ]
    rep = classify_scale_ins(rows, symbols=frozenset({"NAS100"}))
    n = rep["symbols"]["NAS100"]
    assert n["first_n"] == 2
    assert n["scale_n"] == 1
    assert n["scale_net_r"] == -1.0
    assert n["counterfactual_net_r"] == -0.5
    assert rep["totals"]["scale_bleed_r"] == -1.0


def test_filter_drops_other_symbols():
    rows = [
        {"symbol": "US30", "fill_time": 1, "exit_time": 2, "r_realised": -5.0},
        {"symbol": "XAUUSD", "fill_time": 1, "exit_time": 2, "r_realised": 1.0},
    ]
    rep = classify_scale_ins(rows, symbols=frozenset({"XAUUSD"}))
    assert "US30" not in rep["symbols"]
    assert rep["symbols"]["XAUUSD"]["live_net_r"] == 1.0
