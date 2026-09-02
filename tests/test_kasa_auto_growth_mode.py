"""kasa_auto must not shrink lot/margin on a flat book with headroom."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _load():
    spec = importlib.util.spec_from_file_location(
        "kasa_auto", Path(__file__).resolve().parents[1] / "scripts" / "kasa_auto.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_flat_growth_mode_skips_downward_patch():
    mod = _load()
    plan = mod.compute_kasa_targets(
        equity=200.0,
        leverage=500.0,
        n_enabled=4,
        global_free_slots=1,
        margin_usage_pct=0.0,
        max_margin_usage_pct=81.0,
        lot_multiplier=1.05,
        max_concurrent_risk_pct=46.0,
        zero_lot=0,
    )
    assert "max_margin_usage_pct" not in plan["patch"]
    assert "lot_multiplier" not in plan["patch"]


def test_high_leverage_small_account_gets_higher_margin_floor():
    mod = _load()
    plan = mod.compute_kasa_targets(
        equity=200.0,
        leverage=500.0,
        n_enabled=4,
        global_free_slots=1,
        margin_usage_pct=0.0,
        max_margin_usage_pct=55.0,
        lot_multiplier=0.7,
        max_concurrent_risk_pct=46.0,
        zero_lot=0,
    )
    assert plan["targets"]["max_margin_usage_pct"] >= 78.0
    assert plan["patch"].get("max_margin_usage_pct", 0) >= 78.0
