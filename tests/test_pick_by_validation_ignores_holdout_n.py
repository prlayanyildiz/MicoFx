"""Family/TF near-ties must not read holdout trade count.

Found in BR: ``_pick_by_validation`` broke a 5% validation-score band with
``validation.trades + holdout.trades``. Swapping holdout n flipped the
winner while validation was identical — the untouched slice leaked into
selection.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


def _row(strategy: str, val_n: int, hold_n: int, score: float = 10.0) -> dict:
    return {
        "strategy": strategy,
        "validated": True,
        "best": {
            "validation": {"score": score, "trades": val_n},
            "holdout": {"trades": hold_n, "score": 1.0},
        },
    }


def test_swapping_holdout_n_does_not_change_a_validation_tie():
    """t3_stoch vs wavetrend_flip, same validation score and n, opposite holdout n."""
    opt = Optimizer.__new__(Optimizer)
    a_hi = _row("t3_stoch", 20, 999)
    b_lo = _row("wavetrend_flip", 20, 1)
    a_lo = _row("t3_stoch", 20, 1)
    b_hi = _row("wavetrend_flip", 20, 999)
    left = opt._pick_by_validation([a_hi, b_lo])["strategy"]
    right = opt._pick_by_validation([a_lo, b_hi])["strategy"]
    assert left == right, (
        f"holdout n flipped the tie: {left} vs {right} — untouched slice leaked")
