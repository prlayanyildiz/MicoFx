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


def test_openable_slots_are_not_a_top_chip():
    """Per-symbol cap left the strip; free slots are not a second count."""
    assert 'lbl: "Pozisyon"' not in JS
    assert "max_positions_per_symbol" not in JS


def test_daily_limit_is_not_a_top_chip():
    """Operator 27.08: kapali limit still printed 'Gunluk Limit / kapali'."""
    assert 'lbl: "Gunluk Limit"' not in JS
    assert "Gunluk limit normal" not in JS


def test_concurrent_risk_is_not_a_top_chip():
    """Operator 27.08: the 30% 1R tavan left; STOPSUZ rides on Acik K/Z."""
    assert 'lbl: "Eszamanli Risk"' not in JS
    start = JS.index('lbl: "Acik K/Z"')
    blob = JS[start:JS.index("lbl:", JS.index("{ lbl:", start + 1) + 1)]
    assert "STOPSUZ" in blob


def test_global_lot_card_is_not_on_the_ai_strip():
    """System lot_multiplier left; AI risk_scale already rides on Gun."""
    assert 'lbl: "Global Lot Carpani"' not in JS


def test_ai_risk_scale_is_on_the_account_strip():
    """It had its own card; it now rides on today's P&L chip.

    The multiplier is a consequence of the daily drawdown, so it reads better
    beside the day's result than alone. What must not change is that it stays
    visible: it cut every lot to 0.40 for a whole session while the panel
    said nothing.
    """
    assert "ai.risk_scale" in JS
    start = JS.index('lbl: "Gun"')
    limit = JS[start:JS.index("lbl:", JS.index("{ lbl:", start + 1) + 1)]
    assert "lot x" in limit, "the multiplier left the day chip"
    assert "ai.risk_scale" in limit


def test_a_cost_over_the_live_gate_is_marked():
    assert "esik %" in JS
    assert "max_cost_pct_of_risk" in JS
