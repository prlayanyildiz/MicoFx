"""BE lock must fire at exactly breakeven_at_r R (float-safe).

XAU sell geometry: at profit == 1.5 * risk_dist, reconstructing
``entry - (entry - profit)`` undershoots the threshold by ~1e-13, so
overlay_stop skipped BE and left only a trail target that min_step refused.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.exits import overlay_stop


def test_sell_be_locks_at_exact_threshold_despite_float_reconstruction():
    entry = 4470.48
    risk = 6.740000000000691  # live SL 4477.22 - entry
    atr = 6.42652
    profit = 1.5 * risk
    ref = entry - profit
    # The live bug: entry - ref is a hair under 1.5 * risk.
    assert (entry - ref) < 1.5 * risk
    target = overlay_stop(
        is_buy=False, entry=entry, ref=ref, atr=atr,
        trail_start_atr=0.4, trail_step_atr=2.5, trail_mode="atr",
        struct_sl=None, breakeven_at_r=1.5, original_risk=risk,
    )
    assert target == pytest.approx(entry)


def test_buy_be_locks_when_reconstructed_profit_undershoots_threshold():
    entry = 100.0
    risk = 1.0
    atr = 1.0
    # Closed bar a hair under 1.5R after float noise — still BE.
    ref = entry + 1.5 * risk - 1e-13
    assert (ref - entry) < 1.5 * risk
    target = overlay_stop(
        is_buy=True, entry=entry, ref=ref, atr=atr,
        trail_start_atr=3.0, trail_step_atr=2.2, trail_mode="atr",
        struct_sl=None, breakeven_at_r=1.5, original_risk=risk,
    )
    assert target == pytest.approx(entry)
