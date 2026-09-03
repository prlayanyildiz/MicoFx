"""F8: shakeout widens relatively, not to an absolute 2.0 ATR.

Absolute floor muted mtf 0.5→2.0 (4×) on $248 → T1 skip. Relative
``max(base, min(base*1.5, 2.0))`` keeps strategy character while still
protecting a streak.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.risk import shakeout_sl_atr_mult


def _sl(symbol: str, n: int) -> list[dict]:
    return [{"symbol": symbol, "exit_reason": "sl", "r_realised": -1.0}
            for _ in range(n)]


def test_mtf_tight_stop_bumps_one_point_five_not_four_x():
    assert shakeout_sl_atr_mult(0.5, "NAS100", _sl("NAS100", 3)) == 0.75


def test_burst_one_point_zero_becomes_one_point_five():
    assert shakeout_sl_atr_mult(1.0, "GER40", _sl("GER40", 3)) == 1.5


def test_jpn_point_seven_becomes_one_point_zero_five():
    assert shakeout_sl_atr_mult(0.7, "JPN225", _sl("JPN225", 3)) == 1.05


def test_already_wide_stop_is_still_not_pulled_in():
    assert shakeout_sl_atr_mult(2.5, "US30", _sl("US30", 5)) == 2.5
