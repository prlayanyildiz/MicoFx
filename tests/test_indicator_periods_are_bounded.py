"""A negative indicator period was accepted with HTTP 200 and silently became 1.

``_SYMBOL_RISK_BOUNDS`` range-checks the exit and cost axes - sl_atr_mult,
trail_start_atr, trail_step_atr, commission_per_lot - and nothing else. The
indicator periods went through untouched, which indicators.py already says out
loud in ema()'s docstring:

    Reachable, not theoretical. ``pull_fast`` feeds this directly and both
    POST /api/symbols/{symbol} and POST /api/opt/params accept a negative
    value with HTTP 200 - the bounds checks there only cover the exit axes.

Nothing crashes, because every length-taking helper in indicators.py clamps
with ``max(1, int(length))`` - that was fixed for ema and wilder already. The
damage is quieter: the config stores and the panel displays a period the system
does not use. Set t3_length to -5 and the symbol keeps trading a T3 of length 1
while every screen says -5, and an optimiser grid carrying one searches a
degenerate point that reports as a real one.

Only the integer periods are bounded. The float axes are deliberately left
alone because zero means something there - adx_max and cost_rank_max carry
"0 disables" in models.py beside them. A period of zero has no such reading;
a moving average over no bars is not a disabled filter, it is a mistake.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

from micofx.web.app import _INDICATOR_PERIOD_BOUNDS, _validate_risk_bounds


def _check(patch):
    _validate_risk_bounds(patch, bounds=_INDICATOR_PERIOD_BOUNDS)


# ------------------------------------------------------------- the defect

@pytest.mark.parametrize("field", ["t3_length", "rsi_length", "stoch_length",
                                   "atr_period"])
def test_a_negative_period_is_refused(field):
    with pytest.raises(HTTPException) as exc:
        _check({field: -5})
    assert exc.value.status_code == 400
    assert field in str(exc.value.detail)


@pytest.mark.parametrize("field", ["t3_length", "rsi_length", "stoch_length"])
def test_a_zero_period_is_refused(field):
    """A moving average over no bars is a mistake, not a disabled filter."""
    with pytest.raises(HTTPException):
        _check({field: 0})


def test_the_message_names_the_field_and_the_bound():
    with pytest.raises(HTTPException) as exc:
        _check({"t3_length": 0})
    detail = str(exc.value.detail)
    assert "t3_length" in detail and "1" in detail


# --------------------------------------------------- what must keep working

@pytest.mark.parametrize("field,value", [
    ("t3_length", 6), ("rsi_length", 9),
    ("stoch_length", 9), ("trail_lookback", 5),
])
def test_the_values_the_live_book_actually_runs_are_accepted(field, value):
    _check({field: value})


def test_the_float_axes_that_use_zero_to_disable_are_not_in_this_table():
    """adx_max and cost_rank_max say "0 disables" in models.py. Bounding them
    at 1 would refuse a live config."""
    for field in ("adx_max", "cost_rank_max"):
        assert field not in _INDICATOR_PERIOD_BOUNDS


def test_an_absurdly_long_period_is_refused():
    with pytest.raises(HTTPException):
        _check({"t3_length": 100000})


def test_a_missing_or_null_field_is_left_alone():
    _check({})
    _check({"t3_length": None})


def test_the_exit_axes_still_have_their_own_table():
    """This adds a table, it does not replace the one that already existed."""
    from micofx.web.app import _SYMBOL_RISK_BOUNDS
    assert "sl_atr_mult" in _SYMBOL_RISK_BOUNDS
    assert "commission_per_lot" in _SYMBOL_RISK_BOUNDS
