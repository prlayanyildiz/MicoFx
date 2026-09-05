"""trail_exec pick: charged net_r + neighbor-spike reject (US30 3.6)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.trail_exec import best_trail_upgrade


def test_best_trail_rejects_us30_edge_spike():
    """Live 2.2; 3.6 +8R but neighbors collapsed — curve-fit edge."""
    scored = {
        1.8: {"net_r": 33.0, "profit_factor": 1.28, "trades": 260},
        2.0: {"net_r": 31.6, "profit_factor": 1.26, "trades": 256},
        2.2: {"net_r": 29.4, "profit_factor": 1.23, "trades": 254},
        2.5: {"net_r": 26.9, "profit_factor": 1.20, "trades": 249},
        2.8: {"net_r": 13.6, "profit_factor": 1.10, "trades": 246},
        3.2: {"net_r": 10.7, "profit_factor": 1.07, "trades": 243},
        3.6: {"net_r": 37.8, "profit_factor": 1.27, "trades": 233},
    }
    assert best_trail_upgrade(2.2, scored, min_delta_r=8.0) is None


def test_best_trail_accepts_jpn_monotonic_widen():
    scored = {
        2.2: {"net_r": 123.0, "profit_factor": 1.51, "trades": 359},
        2.5: {"net_r": 113.7, "profit_factor": 1.48, "trades": 355},
        2.8: {"net_r": 148.3, "profit_factor": 1.64, "trades": 349},
        3.2: {"net_r": 152.9, "profit_factor": 1.68, "trades": 341},
        3.6: {"net_r": 158.4, "profit_factor": 1.72, "trades": 332},
    }
    pick = best_trail_upgrade(2.8, scored, min_delta_r=8.0)
    assert pick is not None
    assert pick["trail_step_atr"] == 3.6
    assert pick["net_r"] == 158.4


def test_best_trail_keeps_when_live_best():
    scored = {
        2.8: {"net_r": 92.0, "profit_factor": 1.23, "trades": 579},
        3.2: {"net_r": 103.8, "profit_factor": 1.27, "trades": 559},
        3.6: {"net_r": 79.4, "profit_factor": 1.21, "trades": 550},
    }
    assert best_trail_upgrade(3.2, scored, min_delta_r=8.0) is None


def test_best_trail_start_accepts_us30_raise():
    from scripts.trail_exec import best_trail_start_upgrade
    scored = {
        0.5: {"net_r": 29.4, "profit_factor": 1.23, "trades": 254},
        0.6: {"net_r": 32.2, "profit_factor": 1.25, "trades": 253},
        0.8: {"net_r": 32.9, "profit_factor": 1.26, "trades": 251},
        1.2: {"net_r": 35.2, "profit_factor": 1.27, "trades": 249},
        1.5: {"net_r": 39.2, "profit_factor": 1.29, "trades": 248},
        1.8: {"net_r": 41.4, "profit_factor": 1.30, "trades": 248},
        2.0: {"net_r": 31.6, "profit_factor": 1.21, "trades": 248},
    }
    pick = best_trail_start_upgrade(0.5, scored, min_delta_r=8.0)
    assert pick is not None
    assert pick["trail_start_atr"] == 1.8
    assert pick["net_r"] == 41.4
