"""Entry-block honesty + chase/spread auto targets + SpotBrent msa keeper."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import chase_auto_targets, spread_auto_targets
from micofx.entry_pressure import (
    action_fill_rate,
    annotate_entry_row,
    auto_hint,
    chase_pressure,
    clamp_msa_cap,
    competing_block_top,
)


def test_soft_blocks_do_not_fake_zero_action_fill():
    row = {
        "signals": 11,
        "opened": 2,
        "fill_rate": 0.182,
        "blocks": {"seans_disi": 8, "piyasa_kapali": 1},
        "retries": {"seans_disi": 8},
    }
    # 11 - 9 soft = 2 denom → 2/2 = 1.0 hard fill (session was the story).
    assert action_fill_rate(row) == 1.0
    assert auto_hint(row) == "beklenen_soft"


def test_brent_spread_retry_storm_hints_calibrate():
    row = {
        "symbol": "SpotBrent",
        "signals": 29,
        "opened": 5,
        "fill_rate": 0.172,
        "blocks": {
            "hafta_sonu": 7,
            "risk_kademe_aralik": 6,
            "spread": 2,
            "kovalama_asimi": 4,
        },
        "retries": {"spread": 1349, "risk_sembol_limiti": 2674},
    }
    ann = annotate_entry_row(row)
    assert ann["spread_pressure"] >= 10
    assert ann["auto_hint"] == "spread_kalibre"
    assert competing_block_top(row["blocks"]) == 4  # kovalama beats spread unique


def test_bar_doldu_is_soft_not_chase_fodder():
    row = {
        "signals": 7,
        "opened": 4,
        "fill_rate": 0.571,
        "blocks": {"bar_doldu": 3},
        "retries": {"bar_doldu": 793},
    }
    assert auto_hint(row) == "beklenen_soft"
    assert chase_auto_targets([row], set(), {"US30"}) == []


def test_chase_auto_targets_from_kovalama_pressure():
    row = {
        "symbol": "XAUUSD",
        "signals": 12,
        "opened": 3,
        "fill_rate": 0.25,
        "blocks": {"kovalama_asimi": 4, "spread": 1},
        "retries": {"kovalama_asimi": 450},
    }
    assert chase_pressure(row) >= 8
    assert chase_auto_targets([row], set(), {"XAUUSD"}) == ["XAUUSD"]
    assert chase_auto_targets([row], {"XAUUSD"}, {"XAUUSD"}) == []


def test_spread_auto_ignores_capacity_unique_top():
    """risk_sembol unique count must not veto retry-storm spread calibrate."""
    row = {
        "symbol": "SpotBrent",
        "signals": 20,
        "opened": 2,
        "fill_rate": 0.10,
        "blocks": {"risk_sembol_limiti": 15, "spread": 2},
        "retries": {"spread": 600},
    }
    assert spread_auto_targets([row], set(), {"SpotBrent"}) == ["SpotBrent"]


def test_spotbrent_msa_ceiling_keeper():
    assert clamp_msa_cap("SpotBrent", 0.08) == 0.06
    assert clamp_msa_cap("SpotBrent", 0.05) == 0.05
    assert clamp_msa_cap("US30", 0.10) == 0.10


def test_propose_msa_refuses_brent_widen(monkeypatch):
    from scripts import msa_exec

    row = {
        "symbol": "SpotBrent",
        "timeframe": "M30",
        "max_spread_atr": 0.06,
        "strategy": "mtf_pullback",
    }

    def fake_gate_pick(_row, best, **_k):
        return {
            "max_spread_atr": 0.08,
            "net_r": 99.0,
            "live_msa": 0.06,
            "live_net_r": 50.0,
            "live_pf": 1.2,
            "profit_factor": 1.25,
        }

    monkeypatch.setattr(msa_exec, "_score_msa", lambda *_a, **_k: {})
    monkeypatch.setattr("scripts.exec_gates.gate_pick", fake_gate_pick)
    assert msa_exec.propose_msa_upgrade(row) is None
