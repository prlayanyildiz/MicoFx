"""Incumbent replay called client.bars() again, so a long run could
compare the candidate to a later window. Found 15.08 (Codex + Claude):
AR4 closed stamp-vs-fresh; this is the leftover — two snapshots.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


class _Sentinel:
    pass


def test_holdout_uses_run_snapshot_instead_of_a_second_fetch():
    snap = _Sentinel()
    opt = object.__new__(Optimizer)
    opt._bar_snap = {("JPN225", "M15"): snap}

    class _Client:
        def bars(self, *a, **k):
            raise AssertionError("second bars() fetch during incumbent replay")

    opt.client = _Client()
    assert opt._bars_for_holdout("JPN225", "M15") is snap


def test_missing_snapshot_falls_back_to_client():
    opt = object.__new__(Optimizer)
    opt._bar_snap = {}
    marker = _Sentinel()

    class _Client:
        def bars(self, symbol, tf, want):
            return marker

    opt.client = _Client()
    opt.store = type("S", (), {"opt_params": lambda self: {}})()
    assert opt._bars_for_holdout("JPN225", "M15") is marker
