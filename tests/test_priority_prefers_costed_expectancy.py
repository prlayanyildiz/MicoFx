"""Slot priority must prefer stamped holdout_costed expectancy when present.

At ~$232 only ~2 concurrent seats fit. Paper holdout ranks US30 0.156 above
NAS 0.105, but charged expectancy is 0.099 vs 0.046 — and GER stays 0.169.
Fix B selected on costed_e; the open-loop race still read paper until now.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import Supervisor


def test_holdout_expectancy_prefers_costed_stamp():
    cfg = SymbolConfig(
        symbol="US30",
        opt_summary={
            "holdout": {"expectancy": 0.156, "net_r": 43.0, "trades": 276},
            "holdout_costed": {
                "expectancy": 0.099, "net_r": 1.68, "trades": 17,
            },
        },
    )
    assert Supervisor.holdout_expectancy(cfg) == 0.099


def test_holdout_expectancy_falls_back_to_paper_without_costed():
    cfg = SymbolConfig(
        symbol="US30",
        opt_summary={
            "holdout": {"expectancy": 0.156, "net_r": 43.0, "trades": 276},
        },
    )
    assert Supervisor.holdout_expectancy(cfg) == 0.156


def test_priority_ranks_costed_ger_above_paper_flattered_us30():
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
