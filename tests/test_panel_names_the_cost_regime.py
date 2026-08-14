"""V1 panel copy: regime label, per-symbol slot, AI scale, cost-gate mark."""
from __future__ import annotations

from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static" / "app.js"
      ).read_text(encoding="utf-8")


def test_monthly_projection_names_the_cost_regime():
    assert "maliyetsiz OPT" in JS
    assert "projected_costed_monthly" in JS
    assert "MALIYETLI DILIM NEGATIF" in JS


def test_openable_slots_name_the_per_symbol_cap():
    assert "sembol basi" in JS
    assert "max_positions_per_symbol" in JS


def test_ai_risk_scale_is_on_the_account_strip():
    assert "AI Lot Carpani" in JS
    assert "ai.risk_scale" in JS


def test_a_cost_over_the_live_gate_is_marked():
    assert "esik %" in JS
    assert "max_cost_pct_of_risk" in JS
