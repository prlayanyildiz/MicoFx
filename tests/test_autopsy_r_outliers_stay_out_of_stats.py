"""Autopsy |R| outliers must not poison shakeout or report means.

NAS100 #324075699 flatten cash −$9.22 stamped r_realised≈−195 when the
1R denominator collapsed (soft-restart / tiny original_sl). Cash is truth;
|R|>20 is not a trade outcome.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.risk import (
    AUTOPSY_R_ABS_MAX,
    autopsy_r_usable,
    sanitize_autopsy_r,
    shakeout_sl_atr_mult,
)


def test_sane_r_is_usable():
    assert autopsy_r_usable({"r_realised": -1.0})
    assert autopsy_r_usable({"r_realised": 3.01})


def test_nas_style_outlier_is_not_usable():
    assert not autopsy_r_usable({"r_realised": -194.94})
    assert not autopsy_r_usable({"r_realised": 25.0})


def test_missing_r_stays_usable_for_non_r_paths():
    assert autopsy_r_usable({})
    assert autopsy_r_usable({"r_realised": None})


def test_sanitize_nulls_outlier_r_keeps_cash():
    row = {"r_realised": -194.94, "profit": -9.22, "exit_reason": "flatten"}
    out = sanitize_autopsy_r(row)
    assert out["r_realised"] is None
    assert out["profit"] == -9.22
    assert out.get("r_outlier") is True
    assert row["r_realised"] == -194.94  # input not mutated


def test_sanitize_leaves_sane_rows_alone():
    row = {"r_realised": -1.0, "profit": -3.98}
    assert sanitize_autopsy_r(row) == row


def test_outlier_does_not_count_as_shakeout_death():
    """Even if mislabelled sl, absurd R must not trip the floor."""
    rows = [{"symbol": "NAS100", "exit_reason": "sl", "r_realised": -194.94}
            for _ in range(5)]
    assert shakeout_sl_atr_mult(1.0, "NAS100", rows) == 1.0


def test_abs_max_is_the_documented_gate():
    assert AUTOPSY_R_ABS_MAX == 20.0
