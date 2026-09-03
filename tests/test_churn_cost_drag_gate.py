"""Churn F5: primary flip refuses when charged holdout keeps < half of paper net."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


def test_cost_drag_rejects_wrong_family_trap():
    # GER40 + burst: charged +9 / paper +156 → ~6% kept
    reason = Optimizer.cost_drag_reject(156.0, 9.0)
    assert "maliyet drag" in reason


def test_cost_drag_passes_healthy_retention():
    # GER40 + channel_break: 174.7 / 240.4 ≈ 73%
    assert Optimizer.cost_drag_reject(240.4, 174.7) == ""


def test_cost_drag_helper_threshold_examples():
    # JPN225 burst 75.3/168.1 ≈ 45% — below 0.5 (helper rejects; apply skips
    # same-family so live JPN re-tune still works).
    assert "maliyet drag" in Optimizer.cost_drag_reject(168.1, 75.3)
    assert Optimizer.cost_drag_reject(168.1, 85.0) == ""


def test_cost_drag_skips_nonpositive_paper():
    assert Optimizer.cost_drag_reject(0.0, 10.0) == ""
    assert Optimizer.cost_drag_reject(-5.0, 1.0) == ""
