"""Kasa auto-tune targets scale with equity and leverage."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.kasa_auto import compute_kasa_targets


def test_high_leverage_small_equity_targets_conservative_lot():
    plan = compute_kasa_targets(
        equity=200, leverage=500, n_enabled=4,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=85, lot_multiplier=1.0, max_concurrent_risk_pct=50,
    )
    assert plan["targets"]["lot_multiplier"] == 0.85
    assert plan["targets"]["max_margin_usage_pct"] >= 55


def test_equity_growth_raises_lot_multiplier():
    small = compute_kasa_targets(
        equity=200, leverage=500, n_enabled=4,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=70, lot_multiplier=0.85, max_concurrent_risk_pct=40,
    )
    big = compute_kasa_targets(
        equity=1500, leverage=500, n_enabled=4,
        global_free_slots=2, margin_usage_pct=10,
        max_margin_usage_pct=75, lot_multiplier=1.0, max_concurrent_risk_pct=40,
    )
    assert big["targets"]["lot_multiplier"] > small["targets"]["lot_multiplier"]


def test_lot_blocks_bump_lot_only_when_live_lots_ok():
    blocked = compute_kasa_targets(
        equity=200, leverage=500, n_enabled=4,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=68, lot_multiplier=0.85, max_concurrent_risk_pct=46,
        lot_blocks=38,
    )
    assert blocked["targets"]["lot_multiplier"] > 0.85
    assert blocked["targets"]["max_margin_usage_pct"] == 68  # no marj bump from stale counters

    zero = compute_kasa_targets(
        equity=200, leverage=500, n_enabled=4,
        global_free_slots=0, margin_usage_pct=0,
        max_margin_usage_pct=68, lot_multiplier=0.85, max_concurrent_risk_pct=46,
        zero_lot=2,
    )
    assert zero["targets"]["max_margin_usage_pct"] > 68
