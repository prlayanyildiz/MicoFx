"""A candidate may not hand the broker most of what it earns.

MAX_COST_PER_TRADE_R caps cost against the trade's RISK, so it answers "is this
instrument expensive?" and never "can this candidate's own edge carry what it
costs?". Those come apart at the thin end.

Measured on the live book, cost as a share of gross edge:

    XAUUSD    5%   NAS100  9%   GBPUSD  9%   ...   CADJPY 35%
    CA60     43%   COPPER 45%   US30   46%   COFFEE 51%   USDJPY 58%

USDJPY hands over 58% of everything it makes and passes the absolute gate
(0.16 < 0.25) because its gross edge is only 0.277R. XAUUSD could carry 0.22R
of cost on a 0.476R gross edge and is charged 0.025. One ceiling, opposite
verdicts warranted - hence the second, relative one.
"""
from __future__ import annotations

import pytest

from micofx.optimizer import Optimizer


def _best(expectancy: float, cost: float, **over):
    """A candidate that clears every gate except, possibly, the cost ones."""
    slice_ok = {"trades": 40, "net_r": 8.0, "profit_factor": 1.5, "score": 2.0}
    hold = {**slice_ok, "expectancy": expectancy, "cost_per_trade_r": cost}
    return {
        "holdout": {**hold, **over.pop("holdout", {})},
        "validation": {**slice_ok, "expectancy": expectancy},
        "selection": {**slice_ok, "expectancy": expectancy},
        "positive_ratio": 1.0,
        "score": 2.0,
        **over,
    }


def _reject(best):
    # cfg=None skips the incumbent comparison; store=None takes the 0.6 default
    # min_positive_ratio. Both are the secondary-screening path.
    opt = object.__new__(Optimizer)
    opt.store = None
    return Optimizer.reject_reason(opt, None, best)


# --------------------------------------------------------------- the live cases

@pytest.mark.parametrize("symbol,cost,expectancy,share", [
    ("USDJPY", 0.160, 0.117, 58),
    ("COFFEE", 0.077, 0.075, 51),
])
def test_the_two_symbols_over_half_are_refused(symbol, cost, expectancy, share):
    # Both pass the absolute ceiling comfortably - that is the whole point.
    assert cost <= Optimizer.MAX_COST_PER_TRADE_R
    assert _reject(_best(expectancy, cost)) == "maliyet brut kenarin cogunu yiyor"


@pytest.mark.parametrize("symbol,cost,expectancy", [
    ("US30", 0.062, 0.072),      # 46% - expensive, but under half
    ("COPPER", 0.097, 0.118),    # 45%
    ("CA60", 0.109, 0.145),      # 43%
    ("CADJPY", 0.093, 0.171),    # 35%
    ("XAUUSD", 0.025, 0.451),    # 5%
    ("SPA35", 0.221, 0.493),     # 31% - the highest absolute cost in the book
])
def test_everything_at_or_under_half_still_passes(symbol, cost, expectancy):
    assert _reject(_best(expectancy, cost)) == ""


def test_a_fat_edge_may_carry_a_high_absolute_cost():
    # SPA35's 0.221 is nearly at the absolute ceiling and correctly allowed:
    # the edge that carries it is 0.714R gross.
    assert _reject(_best(expectancy=0.493, cost=0.221)) == ""


def test_the_absolute_ceiling_still_bites_on_its_own():
    # A fat edge does not buy unlimited cost - the two gates are independent.
    assert _reject(_best(expectancy=2.0, cost=0.30)) == \
        "islem maliyeti riske gore cok yuksek"


# ------------------------------------------------------------------ the boundary

def test_exactly_half_is_allowed():
    assert _reject(_best(expectancy=0.10, cost=0.10)) == ""


def test_a_hair_over_half_is_not():
    assert _reject(_best(expectancy=0.10, cost=0.1002)) == \
        "maliyet brut kenarin cogunu yiyor"


def test_a_costless_candidate_is_unaffected():
    assert _reject(_best(expectancy=0.20, cost=0.0)) == ""


def test_the_gate_reports_itself_distinctly():
    # The UI shows this string to explain why an apply was skipped, so it must
    # not be confused with the absolute ceiling's message.
    assert _reject(_best(0.117, 0.160)) != _reject(_best(2.0, 0.30))
