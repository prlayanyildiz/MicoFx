"""The pool starves at the tail because the atom of work is a whole sweep.

Measured on the 31.08 US30 run: 14 workers, and for the last ten minutes of a
62-minute search only three were burning CPU while eleven sat idle. Nothing was
wedged - the queue was simply empty except for a few long sweeps that had been
submitted last.

A sweep is one (symbol, timeframe, family) and they are wildly uneven: the
shipped grids run from ichimoku's 1080 points to dual_t3's 2,073,600, and
coverage_budget deliberately hands the bigger grids a bigger sampled budget on
top of that. So a single search is ~24 units of very unequal size on 14 cores,
and submission order was deterministic timeframe x family - i.e. uncorrelated
with cost. Whenever a long sweep landed near the end of the queue it started
last and everyone waited for it alone.

Longest-processing-time first is the standard fix and needs no change to the
worker protocol: start the big ones at t=0 and let the small ones fill the gaps.
Results are unaffected because _finish_symbol re-sorts attempts by ``order``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import longest_first


def _job(order, cost):
    return {"order": order, "cost_hint": cost, "strategy": f"s{order}"}


def test_the_longest_sweep_is_submitted_first():
    jobs = [_job(0, 10), _job(1, 5000), _job(2, 300)]
    assert [j["order"] for j in longest_first(jobs)] == [1, 2, 0]


def test_ties_keep_the_deterministic_order():
    """Two equal-cost sweeps must not swap between runs."""
    jobs = [_job(3, 100), _job(1, 100), _job(2, 100)]
    assert [j["order"] for j in longest_first(jobs)] == [1, 2, 3]


def test_a_missing_hint_sorts_last_and_does_not_raise():
    """An older/partial job dict still schedules rather than blowing up."""
    jobs = [{"order": 0}, _job(1, 7)]
    assert [j["order"] for j in longest_first(jobs)] == [1, 0]


def test_nothing_is_dropped_or_duplicated():
    jobs = [_job(i, (i * 37) % 11) for i in range(20)]
    out = longest_first(jobs)
    assert len(out) == len(jobs)
    assert {id(j) for j in out} == {id(j) for j in jobs}


def test_the_input_list_is_not_reordered_in_place():
    """The caller still owns the deterministic queue for the serial fallback."""
    jobs = [_job(0, 1), _job(1, 999)]
    before = list(jobs)
    longest_first(jobs)
    assert jobs == before
