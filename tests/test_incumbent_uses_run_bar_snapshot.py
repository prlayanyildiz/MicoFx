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


def test_incumbent_replay_does_not_fetch_when_the_snapshot_misses():
    """Keep-line / gate replay must not call client.bars mid-run (AS3)."""
    opt = object.__new__(Optimizer)
    opt._bar_snap = {}

    class _Client:
        def bars(self, *a, **k):
            raise AssertionError("incumbent replay must not live-fetch")

    opt.client = _Client()
    opt.store = type("S", (), {"opt_params": lambda self: {}})()
    assert opt._bars_for_holdout("JPN225", "M30", allow_fetch=False) is None


def test_fresh_incumbent_holdout_is_memoised_for_the_same_cfg():
    opt = object.__new__(Optimizer)
    calls = []

    def once(*a, **k):
        calls.append(1)
        return {"net_r": 1.0, "score": 2.0}

    opt._holdout_costed = once
    cfg = type("C", (), {
        "symbol": "US30", "timeframe": "M5", "strategy": "stoch_flip",
        "sl_atr_mult": 1.0,
    })()
    a = opt._fresh_incumbent_holdout(cfg)
    b = opt._fresh_incumbent_holdout(cfg)
    assert a == b == {"net_r": 1.0, "score": 2.0}
    assert len(calls) == 1
