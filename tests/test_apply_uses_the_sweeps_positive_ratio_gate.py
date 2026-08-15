"""apply's consistency gate must use the threshold the sweep ran under.

``reject_reason`` read ``store.opt_params()['min_positive_ratio']`` at call
time. The ratio it compared was measured on the selection slices. Flipping
the store mid-run (shown live this night) made the same number pass or fail
a different door.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, threshold: float) -> None:
        self._threshold = threshold
        self.system = None

    def opt_params(self):
        return {"min_positive_ratio": self._threshold}

    def get_setting(self, key, default=None):
        return default


def _ok_slices() -> dict:
    slice_ok = {"net_r": 10.0, "trades": 40, "profit_factor": 1.4,
                "expectancy": 0.2, "cost_per_trade_r": 0.0, "score": 8.0}
    return {
        "holdout": dict(slice_ok),
        "validation": dict(slice_ok),
        "selection": dict(slice_ok),
        "positive_ratio": 0.75,
        "score": 8.0,
    }


def _opt(store_threshold: float) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = _Store(store_threshold)
    opt._force_apply = True
    opt._beats_incumbent = lambda *a, **k: True
    opt._generalises = lambda *a, **k: True
    return opt


def test_a_report_threshold_of_0_7_is_used_while_the_store_says_0_9():
    """Sweep started at 0.7; store flipped to 0.9; 0.75 must still pass."""
    best = {**_ok_slices(), "min_positive_ratio": 0.7}
    assert _opt(0.9).reject_reason(None, best) == ""


def test_the_same_ratio_fails_when_the_sweep_itself_used_0_9():
    best = {**_ok_slices(), "min_positive_ratio": 0.9}
    assert _opt(0.9).reject_reason(None, best) == "secim segmentleri arasinda tutarsiz"


def test_an_old_result_without_the_field_falls_back_to_the_store():
    best = _ok_slices()
    assert _opt(0.9).reject_reason(None, best) == "secim segmentleri arasinda tutarsiz"
    assert _opt(0.6).reject_reason(None, best) == ""
