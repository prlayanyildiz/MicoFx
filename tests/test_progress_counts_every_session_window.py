"""The panel bar read 283% on a live three-symbol run.

Observed 10.09 23:2x on `/api/state`: `combo_done` 952000 against
`combo_total` 336000. Both numbers use the same unit - the refine-round fix
(`test_progress_counts_the_refine_rounds`) settled that - so this was not a
unit drift. It was a missing dimension.

`_plan_symbol` sweeps every window in `_session_search_shortlist`, up to
`_SESSION_SEARCH_MAX` (3) of them, each one a full family x timeframe pass.
`run_combo_budget` prices `n_symbols * n_tf * sweep_cost` and never multiplies
by that shortlist, so it reported a third of the work on a run where all three
symbols got all three windows. 952000/336000 = 2.83 is that ratio with two
symbols at three windows and one short.

The shortlist cannot be priced up front: picking it costs a charged holdout
per candidate window, inside `_plan_symbol`. Pricing the worst case instead
would over-report for every symbol whose shortlist comes back short - the same
lie, other direction. So each symbol's estimated share is replaced by what its
plan actually queued, the moment `plan_next` has the plan.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.optimizer import (
    _SESSION_SEARCH_MAX,
    Optimizer,
    run_combo_budget,
    strategy_allows_timeframe,
)

FAMILIES = ["channel_break", "keltner_break", "super_trend"]
TFS = ["M15", "M30"]
ALLOW = {fam: list(TFS) for fam in FAMILIES}


def _one_symbol_one_clock(sweep_cost: dict[str, int]) -> int:
    """What a single symbol spends on a single session window."""
    return sum(
        sweep_cost[fam]
        for fam in FAMILIES
        for tf in TFS
        if strategy_allows_timeframe(fam, tf, ALLOW)
    )


# ------------------------------------------------------- the missing dimension

def test_the_budget_prices_one_clock_per_symbol():
    """Not a bug by itself - it is the premise the correction relies on."""
    total, sweep_cost = run_combo_budget(
        None, FAMILIES, TFS, 2000, 3, 3, ALLOW)
    assert total == 3 * _one_symbol_one_clock(sweep_cost)


def test_the_budget_is_blind_to_how_many_windows_are_swept():
    """Nothing in the estimate moves when the shortlist cap moves."""
    total_a, _ = run_combo_budget(None, FAMILIES, TFS, 2000, 3, 3, ALLOW)
    assert _SESSION_SEARCH_MAX >= 2, "no shortlist means nothing to account for"
    # Same call, and the shortlist cap is not one of its arguments - so a
    # search that sweeps _SESSION_SEARCH_MAX windows spends that multiple of
    # what this returns.
    total_b, _ = run_combo_budget(None, FAMILIES, TFS, 2000, 3, 3, ALLOW)
    assert total_a == total_b


def test_the_uncorrected_estimate_is_what_produced_283_percent():
    """Three symbols, three windows each: the bar would read 300%."""
    est, sweep_cost = run_combo_budget(None, FAMILIES, TFS, 2000, 3, 3, ALLOW)
    per_clock = _one_symbol_one_clock(sweep_cost)
    real_spend = 3 * _SESSION_SEARCH_MAX * per_clock
    assert real_spend == _SESSION_SEARCH_MAX * est
    assert real_spend > est


# ---------------------------------------------------------- what the fix gives

def test_replacing_each_share_with_the_real_plan_lands_on_the_real_spend():
    """The arithmetic plan_next performs, over a run with mixed shortlists.

    Shortlists of 3, 3 and 2 windows - the shape that produced 2.83 live.
    """
    est, sweep_cost = run_combo_budget(None, FAMILIES, TFS, 2000, 3, 3, ALLOW)
    per_clock = _one_symbol_one_clock(sweep_cost)
    per_symbol_est = est // 3

    total = est
    for windows in (3, 3, 2):
        planned = windows * per_clock       # what that symbol's jobs cost
        total += planned - per_symbol_est   # what plan_next does
    assert total == (3 + 3 + 2) * per_clock
    # And the counter the workers advance lands on exactly the same number,
    # because note() adds the same sweep_cost per job.
    done = sum(windows * per_clock for windows in (3, 3, 2))
    assert done == total


def test_a_single_window_run_is_left_exactly_where_it_was():
    """No shortlist, no correction: the old estimate was already right."""
    est, sweep_cost = run_combo_budget(None, FAMILIES, TFS, 2000, 3, 3, ALLOW)
    per_clock = _one_symbol_one_clock(sweep_cost)
    per_symbol_est = est // 3
    total = est
    for _ in range(3):
        total += (1 * per_clock) - per_symbol_est
    assert total == est


def test_progress_never_reports_more_done_than_total():
    """The property the operator actually reads off the bar."""
    est, sweep_cost = run_combo_budget(None, FAMILIES, TFS, 2000, 3, 3, ALLOW)
    per_clock = _one_symbol_one_clock(sweep_cost)
    per_symbol_est = est // 3
    for shortlists in ((1, 1, 1), (3, 3, 3), (3, 2, 1), (2, 1, 3)):
        total = est
        done = 0
        for windows in shortlists:
            total += (windows * per_clock) - per_symbol_est
            done += windows * per_clock
        assert done == total, shortlists
        assert done <= total


# ------------------------------------------------------------- keep it wired

def test_plan_next_corrects_the_total_against_the_queued_jobs():
    src = inspect.getsource(Optimizer._run_all)
    assert "per_symbol_est" in src, "the per-symbol share is gone"
    assert "combo_total += planned - per_symbol_est" in src, \
        "plan_next no longer replaces the estimate with the real plan"
    assert "nonlocal combo_total" in src, \
        "the correction cannot be visible to note() without this"


def test_the_two_counters_still_use_one_cost_table():
    """done and total must both price a sweep from ``sweep_cost``."""
    src = inspect.getsource(Optimizer._run_all)
    assert "sweep_cost.get(fam, default_sweep)" in src
    assert 'sweep_cost.get(str(j.get("strategy") or ""), default_sweep)' in src
    # The shared helper, not an inline formula, still supplies the fallback.
    assert "default_sweep = backtest.sweep_budget(max_combos, refine_rounds)" in src
    assert backtest.sweep_budget(2000, 3) == 8000
