"""The third copy of the same defect: a loss-free slice scored in R, not ratio.

`Result.profit_factor` returned `gross_win_r` - a sum of R - whenever nothing
lost, while `_slice_ok` compares it against MIN_OOS_PF, a ratio of 1.10. Same
silent unit change as `Supervisor._pf` and `Supervisor._judge` carried.

The consequence runs the wrong way here: it REJECTS. `_slice_ok` decides
whether an out-of-sample slice counts as having paid, and a slice is only
tested once it already cleared MIN_TEST_TRADES (25) and net_r > 0. Twenty-five
winning trades and no losers at +0.08R each is 2.00R, scored as "PF 2.00" and
thrown out for missing a 1.10 profit-factor floor it cannot fail on merit -
there is no loss for the wins to be a multiple of.

Note this direction ADMITS configurations that were previously refused, so it
is worth watching which slices newly pass.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.backtest import (
    MIN_OOS_PF,
    MIN_TEST_TRADES,
    PF_NO_LOSSES,
    Result,
    _slice_ok,
)


def _res(win_r: float, loss_r: float = 0.0, trades: int = MIN_TEST_TRADES) -> Result:
    return Result(trades=trades, wins=trades, losses=0,
                  net_r=win_r - loss_r, gross_win_r=win_r, gross_loss_r=loss_r)


# ------------------------------------------------------- the unit must not change

@pytest.mark.parametrize("win_r", [0.96, 0.10, 5.0, 40.0])
def test_a_slice_with_no_losses_scores_the_same_whatever_it_earned(win_r):
    assert _res(win_r).profit_factor == PF_NO_LOSSES


def test_the_total_r_no_longer_decides():
    assert _res(0.10).profit_factor == _res(40.0).profit_factor


# ------------------------------------------------------------ the reachable gate

def test_a_flawless_slice_is_not_rejected_for_being_small():
    """Many winners, nothing lost — must clear as a ratio, not an R sum."""
    slice_dict = {"net_r": 2.0, "trades": MIN_TEST_TRADES,
                  "profit_factor": _res(2.0).profit_factor}
    assert _slice_ok(slice_dict), "kayipsiz dilim R toplami kucuk diye elendi"


def test_the_floor_constant_is_still_a_ratio():
    assert MIN_OOS_PF > 1.0
    assert PF_NO_LOSSES > MIN_OOS_PF


# ------------------------------------------------------- what must keep working

def test_a_real_ratio_is_untouched():
    assert _res(2.0, 1.0).profit_factor == pytest.approx(2.0)
    assert _res(1.0, 2.0).profit_factor == pytest.approx(0.5)


def test_a_losing_slice_is_still_rejected():
    assert not _slice_ok({"net_r": -1.0, "trades": 50, "profit_factor": 0.5})


def test_a_weak_ratio_is_still_rejected():
    r = _res(1.0, 1.0)                      # PF 1.00, under the 1.10 floor
    assert not _slice_ok({"net_r": 0.5, "trades": 50, "profit_factor": r.profit_factor})


def test_a_thin_slice_is_still_rejected_even_if_flawless():
    """MIN_TEST_TRADES is the sample bar and this must not bypass it."""
    assert not _slice_ok({"net_r": 1.0, "trades": MIN_TEST_TRADES - 1,
                          "profit_factor": _res(1.0).profit_factor})


def test_a_slice_that_traded_nothing_is_zero():
    assert Result().profit_factor == 0.0
    assert not _slice_ok({"net_r": 0.0, "trades": 0, "profit_factor": 0.0})


def test_the_score_is_json_safe():
    import json
    encoded = json.dumps({"pf": _res(0.5).profit_factor})
    assert "Infinity" not in encoded and "NaN" not in encoded, encoded
