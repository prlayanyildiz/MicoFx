"""Kasa auto-tune: margin% dial drives lot_multiplier + concurrent."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.kasa_auto import compute_kasa_targets


def _plan(eq=247.0, marj=80.0, n=6, lot=1.0, conc=10.0):
    return compute_kasa_targets(
        equity=eq, n_enabled=n,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=marj, lot_multiplier=lot,
        max_concurrent_risk_pct=conc,
    )


def test_margin80_small_book_moderate_lot_and_conc():
    plan = _plan(marj=80)
    t = plan["targets"]
    assert 0.8 <= t["lot_multiplier"] <= 1.5
    assert 5.0 <= t["max_concurrent_risk_pct"] <= 25.0


def test_higher_margin_pct_more_aggressive():
    lo = _plan(marj=40)
    hi = _plan(marj=95)
    assert hi["targets"]["lot_multiplier"] >= lo["targets"]["lot_multiplier"]
    assert hi["targets"]["max_concurrent_risk_pct"] >= lo["targets"]["max_concurrent_risk_pct"]
    assert hi["aggression"] > lo["aggression"]


def test_low_margin_pct_is_minimal():
    plan = _plan(marj=10)
    assert plan["targets"]["lot_multiplier"] <= 0.5


def test_lot_blocks_do_not_widen_when_counters_stale():
    blocked = compute_kasa_targets(
        equity=200, n_enabled=4,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=78, lot_multiplier=0.92, max_concurrent_risk_pct=46,
        lot_blocks=38,
    )
    clean = compute_kasa_targets(
        equity=200, n_enabled=4,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=78, lot_multiplier=0.92, max_concurrent_risk_pct=46,
    )
    assert blocked["targets"]["lot_multiplier"] == clean["targets"]["lot_multiplier"]
