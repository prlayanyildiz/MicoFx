"""msa_exec pick must beat live charged stamp (GER40/US30 patterns)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.msa_exec import best_msa_upgrade


def test_best_msa_upgrade_picks_ger40_sweet_spot():
    scored = {
        0.03: {"net_r": 34.8, "profit_factor": 1.19, "trades": 311,
               "expectancy": 0.11, "max_dd_r": 14.9},
        0.05: {"net_r": 73.8, "profit_factor": 1.34, "trades": 373,
               "expectancy": 0.20, "max_dd_r": 18.3},
        0.08: {"net_r": 63.2, "profit_factor": 1.26, "trades": 413,
               "expectancy": 0.15, "max_dd_r": 14.5},
        0.12: {"net_r": 71.0, "profit_factor": 1.29, "trades": 422,
               "expectancy": 0.17, "max_dd_r": 16.3},
    }
    pick = best_msa_upgrade(0.08, scored, min_delta_r=5.0)
    assert pick is not None
    assert pick["max_spread_atr"] == 0.05
    assert pick["net_r"] == 73.8


def test_best_msa_upgrade_skips_when_live_already_best():
    scored = {
        0.05: {"net_r": 73.8, "profit_factor": 1.34, "trades": 373,
               "expectancy": 0.20, "max_dd_r": 18.3},
        0.08: {"net_r": 63.2, "profit_factor": 1.26, "trades": 413,
               "expectancy": 0.15, "max_dd_r": 14.5},
    }
    assert best_msa_upgrade(0.05, scored, min_delta_r=5.0) is None


def test_best_msa_upgrade_us30_escapes_trough():
    scored = {
        0.06: {"net_r": 30.8, "profit_factor": 1.29, "trades": 214,
               "expectancy": 0.144, "max_dd_r": 12.0},
        0.08: {"net_r": 25.0, "profit_factor": 1.20, "trades": 240,
               "expectancy": 0.104, "max_dd_r": 14.0},
        0.10: {"net_r": 29.8, "profit_factor": 1.23, "trades": 253,
               "expectancy": 0.118, "max_dd_r": 15.3},
        0.12: {"net_r": 29.4, "profit_factor": 1.23, "trades": 254,
               "expectancy": 0.116, "max_dd_r": 15.3},
    }
    pick = best_msa_upgrade(0.08, scored, min_delta_r=3.0)
    assert pick is not None
    assert pick["max_spread_atr"] == 0.06


def test_best_msa_upgrade_rejects_quantity_over_quality():
    """SpotBrent 14-22: 0.08 +40R but PF/exp/dd worse than 0.05."""
    scored = {
        0.05: {"net_r": 32.0, "profit_factor": 1.23, "trades": 222,
               "expectancy": 0.144, "max_dd_r": 24.4},
        0.08: {"net_r": 40.8, "profit_factor": 1.14, "trades": 487,
               "expectancy": 0.084, "max_dd_r": 35.0},
    }
    assert best_msa_upgrade(0.05, scored, min_delta_r=5.0) is None
