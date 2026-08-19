"""STAMP-1b: live vs stamp, only fields that can change behaviour.

Unread OPT axes must not warn. A max_spread_atr move with
``spread_recalibrated_to`` on the stamp is expected; the same gap without
that record is unexplained.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_restamp_writes_the_replayed_params import _Client, _Store

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer
from micofx.strategy import stamp_fields


def _opt(cfg: SymbolConfig) -> Optimizer:
    return Optimizer(store=_Store(cfg), client=_Client())


def test_unread_stamp_mismatch_is_not_unexpected():
    cfg = SymbolConfig(symbol="GER40", magic=1, strategy="stoch_flip",
                       htf_factor=3, adx_min=20.0, sl_atr_mult=1.2)
    cfg.opt_summary = {
        "params": {"htf_factor": 99, "adx_min": 0.0, "sl_atr_mult": 1.2},
    }
    assert "htf_factor" not in stamp_fields("stoch_flip")
    report = _opt(cfg).stamp_drift()
    row = report["rows"][0]
    fields = [d["field"] for d in row["unexpected"]]
    assert "htf_factor" not in fields
    assert "adx_min" not in fields
    assert report["unexpected"] == 0


def test_a_real_exit_mismatch_is_unexpected():
    cfg = SymbolConfig(symbol="NAS100", magic=1, strategy="mtf_pullback",
                       trail_start_atr=1.0, trail_step_atr=1.8)
    cfg.opt_summary = {
        "params": {"trail_start_atr": 0.8, "trail_step_atr": 2.2,
                   "sl_atr_mult": 1.2, "max_spread_atr": 0.0,
                   "min_atr_ratio": 0.0, "trail_mode": "atr", "trail_lookback": 5},
    }
    report = _opt(cfg).stamp_drift()
    fields = {d["field"] for d in report["rows"][0]["unexpected"]}
    assert "trail_start_atr" in fields
    assert "trail_step_atr" in fields
    assert report["unexpected"] >= 2


def test_spread_calibration_record_is_expected_not_red():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, strategy="burst",
                       max_spread_atr=0.25)
    cfg.opt_summary = {
        "params": {"max_spread_atr": 0.05, "sl_atr_mult": 1.2,
                   "trail_start_atr": 0.8, "trail_step_atr": 0.6,
                   "trail_mode": "atr", "trail_lookback": 5, "min_atr_ratio": 0.0},
        "spread_recalibrated_to": 0.25,
    }
    report = _opt(cfg).stamp_drift()
    row = report["rows"][0]
    assert any(d["field"] == "max_spread_atr" for d in row["calibrated"])
    assert not any(d["field"] == "max_spread_atr" for d in row["unexpected"])


def test_spread_gap_without_a_record_is_red():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, strategy="burst",
                       max_spread_atr=0.25)
    cfg.opt_summary = {
        "params": {"max_spread_atr": 0.05, "sl_atr_mult": 1.2,
                   "trail_start_atr": 0.8, "trail_step_atr": 0.6,
                   "trail_mode": "atr", "trail_lookback": 5, "min_atr_ratio": 0.0},
    }
    report = _opt(cfg).stamp_drift()
    fields = {d["field"] for d in report["rows"][0]["unexpected"]}
    assert "max_spread_atr" in fields


def test_the_drift_report_is_on_the_panel():
    src = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py").read_text(
        encoding="utf-8")
    assert "/api/analysis/stamp-drift" in src
    assert "stamp_drift" in src
