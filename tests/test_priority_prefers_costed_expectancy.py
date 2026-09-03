"""Prefer holdout_costed only when the charged stamp has enough trades.

US30 force-apply stamped holdout_costed n=17 (noise e=0.099) over a solid
cost-free holdout n=276 e=0.156 — slot/budget/autopilot/projection all read
the thin sample. Claude 03.09: require MIN_COSTED_N before preferring costed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import Supervisor


def test_thin_costed_stamp_falls_back_to_paper_holdout():
    """Live US30: costed n=17 must not beat paper n=276."""
    cfg = SymbolConfig(
        symbol="US30",
        opt_summary={
            "holdout": {"expectancy": 0.156, "net_r": 43.09, "trades": 276},
            "holdout_costed": {
                "expectancy": 0.099, "net_r": 1.68, "trades": 17,
            },
        },
    )
    assert Supervisor.holdout_expectancy(cfg) == 0.156


def test_ample_costed_stamp_is_preferred():
    cfg = SymbolConfig(
        symbol="NAS100",
        opt_summary={
            "holdout": {"expectancy": 0.105, "net_r": 172.0, "trades": 1600},
            "holdout_costed": {
                "expectancy": 0.046, "net_r": 72.4, "trades": 1559,
            },
        },
    )
    assert Supervisor.holdout_expectancy(cfg) == 0.046


def test_holdout_expectancy_falls_back_to_paper_without_costed():
    cfg = SymbolConfig(
        symbol="US30",
        opt_summary={
            "holdout": {"expectancy": 0.156, "net_r": 43.0, "trades": 276},
        },
    )
    assert Supervisor.holdout_expectancy(cfg) == 0.156


def test_ger_ample_costed_still_ranks_above_us30_paper_fallback():
    ger = SymbolConfig(
        symbol="GER40",
        opt_summary={
            "holdout": {"expectancy": 0.169, "net_r": 71.0, "trades": 200},
            "holdout_costed": {
                "expectancy": 0.169, "net_r": 71.0, "trades": 200,
            },
        },
    )
    us30 = SymbolConfig(
        symbol="US30",
        opt_summary={
            "holdout": {"expectancy": 0.156, "net_r": 43.0, "trades": 276},
            "holdout_costed": {
                "expectancy": 0.099, "net_r": 1.68, "trades": 17,
            },
        },
    )
    assert Supervisor.holdout_expectancy(ger) > Supervisor.holdout_expectancy(us30)
