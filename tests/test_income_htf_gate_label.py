"""income_dev_loop — htf_gate_label (Claude 11:12)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.income_dev_loop import htf_gate_label


def test_htf_gate_label_off_when_factor_le_1():
    assert htf_gate_label({"htf_mode": "t3", "htf_factor": 0}) == "OFF"
    assert htf_gate_label({"htf_mode": "t3", "htf_factor": 1}) == "OFF"
    assert htf_gate_label({}) == "OFF"


def test_htf_gate_label_on_when_factor_gt_1():
    assert htf_gate_label({"htf_mode": "t3", "htf_factor": 3}) == "ON/3"
    assert htf_gate_label({"htf_mode": "t3", "htf_factor": 6}) == "ON/6"
