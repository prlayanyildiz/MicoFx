"""Kasa auto-tune: leverage dial drives lot_multiplier + concurrent."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.kasa_auto import compute_kasa_targets


def _plan(eq=247.0, lev=50.0, broker=500.0, n=6, lot=1.0, conc=10.0, marj=85.0):
    return compute_kasa_targets(
        equity=eq, leverage=lev, n_enabled=n,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=marj, lot_multiplier=lot,
        max_concurrent_risk_pct=conc, broker_leverage=broker,
    )


def test_lev50_small_book_moderate_lot_and_conc():
    plan = _plan(lev=50, broker=500)
    t = plan["targets"]
    assert 0.8 <= t["lot_multiplier"] <= 1.5
    assert 5.0 <= t["max_concurrent_risk_pct"] <= 25.0
    assert plan["buying_power"] == 247.0 * 50


def test_full_broker_more_aggressive_than_lev50():
    lo = _plan(lev=50, broker=500)
    hi = _plan(lev=500, broker=500)
    assert hi["targets"]["lot_multiplier"] >= lo["targets"]["lot_multiplier"]
    assert hi["targets"]["max_concurrent_risk_pct"] >= lo["targets"]["max_concurrent_risk_pct"]
    assert hi["aggression"] > lo["aggression"]


def test_lev1_is_minimal():
    plan = _plan(lev=1, broker=500)
    assert plan["targets"]["lot_multiplier"] == 0.3
    assert plan["targets"]["max_concurrent_risk_pct"] <= 10.0


def test_lot_blocks_do_not_widen_margin_when_counters_stale():
    blocked = compute_kasa_targets(
        equity=200, leverage=500, n_enabled=4,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=78, lot_multiplier=0.92, max_concurrent_risk_pct=46,
        lot_blocks=38, broker_leverage=500,
    )
    assert abs(blocked["targets"]["lot_multiplier"]
               - compute_kasa_targets(
                   equity=200, leverage=500, n_enabled=4,
                   global_free_slots=1, margin_usage_pct=0,
                   max_margin_usage_pct=78, lot_multiplier=0.92,
                   max_concurrent_risk_pct=46, broker_leverage=500,
               )["targets"]["lot_multiplier"]) < 1e-9

    zero = compute_kasa_targets(
        equity=200, leverage=500, n_enabled=4,
        global_free_slots=0, margin_usage_pct=0,
        max_margin_usage_pct=68, lot_multiplier=0.85, max_concurrent_risk_pct=46,
        zero_lot=2, broker_leverage=500,
    )
    assert zero["targets"]["max_margin_usage_pct"] > 68


def test_base_notional_overrides_ref_scale():
    """When capacity supplies 1x notional, lot = deploy / that sum."""
    # deploy = 0.8 * 247 * 50 = 9880; base=9880 → lot 1.0
    plan = compute_kasa_targets(
        equity=247, leverage=50, n_enabled=6,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=85, lot_multiplier=0.5,
        max_concurrent_risk_pct=10, broker_leverage=500,
        base_notional_at_1x=9880.0,
    )
    assert plan["targets"]["lot_multiplier"] == 1.0
