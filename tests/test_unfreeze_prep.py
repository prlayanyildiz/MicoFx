"""unfreeze_prep — fill_focus + frozen hint helpers."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.unfreeze_prep import (
    book_trail_geometry,
    fill_focus,
    give_back_post_restart,
    post_restart_rows,
    premature_sl_metrics,
    trail_geometry,
    unfreeze_gate_frame,
)


def test_give_back_post_restart_ratio():
    """Claude 12:04: monitor only; mfe>=0.5; split by exit (not a gate)."""
    rows = [
        {"symbol": "XAUUSD", "exit_reason": "sl", "mfe_r": 2.11,
         "left_on_table_r": 3.15, "r_realised": -1.0},
        {"symbol": "XAUUSD", "exit_reason": "trail", "mfe_r": 1.70,
         "left_on_table_r": 1.75, "r_realised": 0.8},
        {"symbol": "BTCUSD", "exit_reason": "trail", "mfe_r": 8.29,
         "left_on_table_r": 4.22, "r_realised": 4.08},
        {"symbol": "XAUUSD", "exit_reason": "sl", "mfe_r": 0.3,
         "left_on_table_r": 0.4},  # below min_mfe_r
    ]
    out = give_back_post_restart(rows)
    assert out["n"] == 3
    assert out["is_gate"] is False
    assert out["by_symbol"]["XAUUSD"]["n"] == 2
    assert out["by_exit"]["trail"]["n"] == 2
    assert out["by_exit"]["sl"]["n"] == 1
    expect = round((3.15 + 1.75 + 4.22) / (2.11 + 1.70 + 8.29), 4)
    assert out["ratio"] == expect


def test_post_restart_rows_use_last_n_by_epoch():
    """exit_time is broker epoch — ISO restart_at string compare finds nothing."""
    rows = [
        {"symbol": "OLD", "exit_time": 100, "mfe_r": 1, "left_on_table_r": 1,
         "exit_reason": "sl"},
        {"symbol": "BTCUSD", "exit_time": 200, "mfe_r": 8.29,
         "left_on_table_r": 4.22, "exit_reason": "trail", "r_realised": 4.08},
    ]
    post = post_restart_rows(rows, n_new=1)
    assert [r["symbol"] for r in post] == ["BTCUSD"]
    assert give_back_post_restart(post)["n"] == 1
    assert give_back_post_restart(post)["by_exit"]["trail"]["n"] == 1


def test_premature_sl_metrics_rate_and_lift():
    """Claude 17:44: official lift uses after_1h_bars >= 3 on both sides."""
    rows = [
        {"exit_reason": "sl", "r_realised": -1.0, "after_1h_bars": 4,
         "after_1h_recovery_r": 1.2},
        {"exit_reason": "sl", "r_realised": -1.0, "after_1h_bars": 4,
         "after_1h_through_entry": True},
        {"exit_reason": "trail", "after_1h_bars": 4, "after_1h_recovery_r": 1.0},
        {"exit_reason": "trail", "after_1h_bars": 4, "after_1h_recovery_r": 0.1},
        {"exit_reason": "sl", "r_realised": 0.5, "after_1h_bars": 4,
         "after_1h_recovery_r": 2.0},
        {"exit_reason": "sl", "r_realised": -1.0, "after_1h_bars": 0,
         "after_1h_recovery_r": 2.0},
        # Dead flatten window — inflates raw non-SL base if kept (Claude 17:44).
        {"exit_reason": "flatten", "after_1h_bars": 1, "after_1h_recovery_r": 0.0},
    ]
    m = premature_sl_metrics(rows)
    assert m["min_after_1h_bars"] == 3
    assert m["sl_denom"] == 2 and m["premature"] == 2
    assert m["rate"] == 1.0
    assert m["non_sl_denom"] == 2 and m["non_sl_recovery_rate"] == 0.5
    assert m["lift"] == 2.0
    assert m["historical_lift_ref"] == 1.437
    # Primary all-exit also K>=3 (excludes flatten bars=1).
    assert m["all_exit_denom"] == 5
    assert m["all_exit_recovery_rate"] == 0.8
    # Diagnostics: raw includes flatten → lower non-SL base → higher lift_nonsl_raw.
    assert m["lift_nonsl_raw"] == round(1.0 / (1 / 3), 3)  # 1 hit / 3 non-sl
    assert m["lift_vs_all"] is not None


def test_unfreeze_gate_frame_phases():
    assert unfreeze_gate_frame(1)["phase"] == "pre_safety"
    assert unfreeze_gate_frame(25)["phase"] == "safety"
    assert unfreeze_gate_frame(25)["per_symbol_premature_floor"] is False
    assert unfreeze_gate_frame(100)["phase"] == "evidence"
    assert unfreeze_gate_frame(100)["premature_is_gate"] is True


def test_fill_focus_defaults_and_rates():
    rows = [
        {"symbol": "US30", "signals": 4, "opened": 1, "fill_rate": 0.25,
         "blocks": {"spread": 2}},
        {"symbol": "XAUUSD", "signals": 9, "opened": 9},
    ]
    out = fill_focus(rows)
    assert out["US30"]["fill_rate"] == 0.25
    assert out["US30"]["actionable_signals"] == 3  # 1 open + 2 spread
    assert out["US30"]["spread_blocks"] == 2
    assert out["GER40"]["signals"] == 0
    assert out["NAS100"]["signals"] == 0


def test_fill_focus_ignores_seans_disi():
    out = fill_focus([{
        "symbol": "NAS100", "signals": 4, "opened": 0, "fill_rate": 0.0,
        "blocks": {"seans_disi": 4},
    }])
    assert out["NAS100"]["actionable_signals"] == 0
    assert out["NAS100"]["action_fill_rate"] == 0.0
    assert out["NAS100"]["signals"] == 4  # raw panel total kept


def test_trail_geometry_xau_giveback_trap():
    """XAU sl0.7/step2.5: trail never beats SL before ~2.57R (> BE@1.5)."""
    g = trail_geometry(
        symbol="XAUUSD",
        sl_atr_mult=0.7,
        trail_start_atr=0.4,
        trail_step_atr=2.5,
        breakeven_at_r=1.5,
    )
    assert g["need_mfe_atr_before_trail_beats_sl"] == 1.8
    assert g["trail_improves_at_r"] == round(1.8 / 0.7, 4)  # ~2.5714
    assert g["trail_arms_at_r"] == round(2.5 / 0.7, 4)
    assert g["trap"] is True
    assert g["monitor_only"] is True
    assert g["breakeven_at_r"] == 1.5


def test_trail_geometry_ger40_not_trap():
    """GER40 sl1.5/step2.2: trail can improve at 1.0R before BE@1.5."""
    g = trail_geometry(
        symbol="GER40",
        sl_atr_mult=1.5,
        trail_start_atr=1.5,
        trail_step_atr=2.2,
        breakeven_at_r=1.5,
    )
    assert g["trail_improves_at_r"] == 1.0  # max(1.5, 0.7)/1.5
    assert g["trap"] is False


def test_book_trail_geometry_lists_traps():
    rows = [
        {"symbol": "XAUUSD", "sl_atr_mult": 0.7, "trail_start_atr": 0.4,
         "trail_step_atr": 2.5, "breakeven_at_r": 1.5},
        {"symbol": "GER40", "sl_atr_mult": 1.5, "trail_start_atr": 1.5,
         "trail_step_atr": 2.2, "breakeven_at_r": 1.5},
        {"symbol": "OTHER", "sl_atr_mult": 0.5, "trail_start_atr": 0.2,
         "trail_step_atr": 3.0, "breakeven_at_r": 1.0},  # not in BOOK
    ]
    out = book_trail_geometry(rows)
    assert out["trap_symbols"] == ["XAUUSD"]
    assert out["wide_symbols"] == ["XAUUSD"]
    assert out["by_symbol"]["XAUUSD"]["trap"] is True
    assert out["by_symbol"]["XAUUSD"]["status"] == "OPTIMUM"
    assert out["by_symbol"]["GER40"]["trap"] is False
    assert "OTHER" not in out["by_symbol"]
    assert out["is_gate"] is False
    assert out["axis_status"] == "AXIS_CLOSED_OPTIMUM"
    assert out["label"] == "OPTIMUM"
