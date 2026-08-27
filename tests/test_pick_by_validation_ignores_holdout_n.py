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


def _row(strategy: str, val_n: int, hold_n: int, score: float = 10.0,
         timeframe: str = "M15") -> dict:
    return {
        "strategy": strategy,
        "timeframe": timeframe,
        "validated": True,
        "best": {
            "validation": {"score": score, "trades": val_n},
            "holdout": {"trades": hold_n, "score": 1.0},
        },
    }


def test_swapping_holdout_n_does_not_change_a_validation_tie():
    """t3_flip vs dual_t3, same validation score and n, opposite holdout n."""
    opt = Optimizer.__new__(Optimizer)
    a_hi = _row("t3_flip", 20, 999)
    b_lo = _row("dual_t3", 20, 1)
    a_lo = _row("t3_flip", 20, 1)
    b_hi = _row("dual_t3", 20, 999)
    left = opt._pick_by_validation([a_hi, b_lo])["strategy"]
    right = opt._pick_by_validation([a_lo, b_hi])["strategy"]
    assert left == right, (
        f"holdout n flipped the tie: {left} vs {right} — untouched slice leaked")


def test_two_scalp_peers_also_ignore_holdout_n():
    """burst vs stoch_flip: holdout n must not hide behind family identity."""
    opt = Optimizer.__new__(Optimizer)
    a_hi = _row("burst", 20, 999)
    b_lo = _row("stoch_flip", 20, 1)
    a_lo = _row("burst", 20, 1)
    b_hi = _row("stoch_flip", 20, 999)
    left = opt._pick_by_validation([a_hi, b_lo])["strategy"]
    right = opt._pick_by_validation([a_lo, b_hi])["strategy"]
    assert left == right, (
        f"holdout n flipped a two-family tie: {left} vs {right}")


def test_timeframe_name_breaks_a_validation_tie_not_list_order():
    """Same family, same validation: winner must not follow whoever was first."""
    opt = Optimizer.__new__(Optimizer)
    h1 = _row("stoch_flip", 20, 1, timeframe="H1")
    m15 = _row("stoch_flip", 20, 999, timeframe="M15")
    first = opt._pick_by_validation([h1, m15])
    second = opt._pick_by_validation([m15, h1])
    # max() on the name, not list order. Holdout n differs on purpose.
    assert first["timeframe"] == second["timeframe"] == "M15"
