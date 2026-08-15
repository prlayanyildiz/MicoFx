"""V1 panel copy: regime label, per-symbol slot, AI scale, cost-gate mark."""
from __future__ import annotations

from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static" / "app.js"
      ).read_text(encoding="utf-8")


def test_monthly_projection_names_the_cost_regime():
    assert "maliyetsiz" in JS
    assert "projected_costed_monthly" in JS
    # Reworded on 15.08: the flag is per symbol and the figure beside it is a
    # sum, so "maliyetli dilim +634 | MALIYETLI DILIM NEGATIF" read as a
    # contradiction on one line.
    assert "bazi semboller maliyetli dilimde negatif" in JS


def test_openable_slots_name_the_per_symbol_cap():
    assert "sembol basi" in JS
    assert "max_positions_per_symbol" in JS


def test_ai_risk_scale_is_on_the_account_strip():
    """It had its own card; it now rides on the daily-limit one.

    The multiplier is a consequence of the daily drawdown, so it reads better
    beside the limit than alone - and alone it was the ninth card, stranded on
    a row of its own. What must not change is that it stays visible: it cut
    every lot to 0.40 for a whole session while the panel said nothing.
    """
    assert "ai.risk_scale" in JS
    limit = JS[JS.index('lbl: "Gunluk Limit"'):]
    assert "lot x" in limit[:400], "the multiplier left the strip entirely"
    assert "ai.risk_scale" in limit[:400]


def test_a_cost_over_the_live_gate_is_marked():
    assert "esik %" in JS
    assert "max_cost_pct_of_risk" in JS
