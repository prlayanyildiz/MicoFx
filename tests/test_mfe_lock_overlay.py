"""MFE profit-lock rungs in overlay_stop (Antigravity 07.09)."""
from __future__ import annotations

import pytest

from micofx.exits import mfe_lock_to_r, overlay_stop


def _kw(**over):
    base = {
        "is_buy": True, "entry": 100.0, "ref": 101.6, "atr": 1.0,
        "trail_start_atr": 10.0, "trail_step_atr": 0.4,
        "trail_mode": "atr", "struct_sl": None, "breakeven_at_r": 0.0,
        "original_risk": 1.0,
    }
    base.update(over)
    return base


def test_mfe_lock_rung1_locks_075r():
    # +1.6R open → lock at +0.75R = 100.75
    sl = overlay_stop(**_kw(
        mfe_lock1_at_r=1.5, mfe_lock1_to_r=0.75,
        mfe_lock2_at_r=2.0, mfe_lock2_to_r=1.25))
    assert sl == pytest.approx(100.75)


def test_mfe_lock_rung2_beats_rung1():
    sl = overlay_stop(**_kw(
        ref=102.1,
        mfe_lock1_at_r=1.5, mfe_lock1_to_r=0.75,
        mfe_lock2_at_r=2.0, mfe_lock2_to_r=1.25))
    assert sl == pytest.approx(101.25)


def test_mfe_lock_uses_peak_after_giveback():
    # Current profit 0.5R but peak was 1.6R → still lock 0.75
    assert mfe_lock_to_r(
        profit=0.5, original_risk=1.0,
        lock1_at_r=1.5, lock1_to_r=0.75,
        lock2_at_r=2.0, lock2_to_r=1.25,
        peak_profit=1.6) == pytest.approx(0.75)
    sl = overlay_stop(**_kw(
        ref=100.5,
        peak_profit=1.6,
        mfe_lock1_at_r=1.5, mfe_lock1_to_r=0.75,
        mfe_lock2_at_r=0.0, mfe_lock2_to_r=0.0))
    assert sl == pytest.approx(100.75)


def test_mfe_lock_off_when_at_r_zero():
    assert overlay_stop(**_kw(mfe_lock1_at_r=0.0, mfe_lock1_to_r=0.75)) is None
