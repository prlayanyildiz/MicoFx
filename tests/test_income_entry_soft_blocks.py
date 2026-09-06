"""income board must surface soft session blocks (NAS seans_disi ≠ fill miss)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.income_dev_loop import render_markdown


def _minimal_report(**overrides):
    base = {
        "ts": "2026-09-04 15:30:00",
        "live": {
            "positions": 0,
            "open_symbols": [],
            "margin_usage_pct": 0,
            "max_margin_usage_pct": 80,
            "mt5_connected": True,
        },
        "opt_job": "done",
        "system": {"lot_multiplier": 1.2, "size_by_edge": True,
                   "max_concurrent_risk_pct": 15.2},
        "supervisor": {},
        "ranked": [],
        "keep_live": [],
        "reopt_ready": [],
        "actions": [],
        "active_symbols": ["NAS100", "JPN225"],
        "entry_blocks": [
            {
                "symbol": "NAS100",
                "signals": 4,
                "opened": 0,
                "fill_rate": 0.0,
                "blocks": {"seans_disi": 4},
            },
            {
                "symbol": "JPN225",
                "signals": 2,
                "opened": 0,
                "fill_rate": 0.0,
                "blocks": {"saat_kapali": 2},
            },
        ],
    }
    base.update(overrides)
    return base


def test_kacan_table_shows_seans_disi_and_saat_kapali():
    md = render_markdown(_minimal_report(), [])
    assert "Seans disi" in md and "Saat kapali" in md, md
    nas_line = next(ln for ln in md.splitlines() if ln.startswith("| NAS100 |"))
    # Sinyal=4 Acilan=0 Fill=%0 Spread=0 ... Seans disi=4
    parts = [p.strip() for p in nas_line.strip("|").split("|")]
    assert parts[0] == "NAS100"
    assert parts[1] == "4"
    assert parts[2] == "0"
    # last soft columns: seans_disi, saat_kapali
    assert parts[-2] == "4", nas_line
    assert parts[-1] == "0", nas_line
    jpn_line = next(ln for ln in md.splitlines() if ln.startswith("| JPN225 |"))
    jparts = [p.strip() for p in jpn_line.strip("|").split("|")]
    assert jparts[-2] == "0", jpn_line
    assert jparts[-1] == "2", jpn_line


def test_nas_fill_line_names_dominant_soft_block():
    md = render_markdown(_minimal_report(nas100_fill={
        "fill_rate": 0.0,
        "actionable_signals": 0,
        "signals": 4,
        "opened": 0,
        "poor_fill": False,
        "dominant_block": "seans_disi",
        "spread_blocks": 0,
    }), [])
    assert "NAS100 fill" in md
    assert "dominant=seans_disi" in md
    assert "spread_blocks=0" in md


def test_render_surfaces_trail_geometry_optimum():
    md = render_markdown(_minimal_report(unfreeze_prep={
        "baseline": {"new_trades": 2, "target": 25},
        "gate_frame": {"phase": "pre_safety"},
        "premature_total": 0,
        "premature_total_post_restart": 0,
        "premature_metrics_post_restart": {},
        "premature_metrics": {},
        "give_back_post_restart": {"ratio": None, "n": 0, "is_gate": False,
                                   "by_exit": {}},
        "trail_geometry": {
            "axis_status": "AXIS_CLOSED_OPTIMUM",
            "wide_symbols": ["XAUUSD"],
            "trap_symbols": ["XAUUSD"],
            "by_symbol": {
                "XAUUSD": {
                    "trail_improves_at_r": 2.5714,
                    "breakeven_at_r": 1.5,
                    "trail_step_atr": 2.5,
                    "sl_atr_mult": 0.7,
                    "why": "wide geometry OPTIMUM: improves@2.57R > BE@1.5",
                },
            },
            "is_gate": False,
        },
        "gate6": {"ok_all": True},
        "safety_checkpoint_ok": False,
        "evidence_gate_ok": False,
        "unfreeze_ready_hint": False,
    }), [])
    assert "geometry=AXIS_CLOSED_OPTIMUM" in md
    assert "wide=['XAUUSD']" in md or 'wide=["XAUUSD"]' in md
    assert "## Trail geometry (AXIS_CLOSED_OPTIMUM — monitor, not a fix)" in md
    assert "XAUUSD: improves@2.5714R > BE@1.5" in md
    assert "geometry_traps=" not in md
    assert "Trail geometry traps" not in md
