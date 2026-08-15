"""``lookback_days = 0`` means "no day limit", not "no bars".

The bar request was ``min(max_bars, days * 86400 / tf_seconds)``, so setting the
day window to zero asked the terminal for zero bars. Every timeframe then filed
as "veri yetersiz (0 bar)" and the search found nothing - switching off the day
window switched off the optimiser.

Caught on 15.08 before a run: the workaround was to park the field at 4000 days
so it could never bind, which put an eleven-year history window on the panel and
read as a deliberate setting rather than as "unused".

Zero as "off" is the convention every other optional ceiling here already uses:
symbol_daily_loss_pct, day_end_flatten_min, htf_factor, max_spread_atr.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer

SRC = inspect.getsource(Optimizer._plan_symbol)


def _want(bar_cap: int, days: int, tf_seconds: int) -> int:
    """The expression under test, kept in one place."""
    per_tf = int(days * 86400 / tf_seconds)
    return min(bar_cap, per_tf) if days > 0 else bar_cap


def test_zero_days_asks_for_the_whole_budget():
    assert _want(90000, 0, 300) == 90000


def test_a_real_day_window_still_binds_when_it_is_the_smaller_one():
    # 30 days of M5 is 8640 bars, well under the budget.
    assert _want(90000, 30, 300) == 8640


def test_the_budget_still_binds_when_the_day_window_is_the_larger_one():
    assert _want(90000, 4000, 300) == 90000


def test_the_guard_is_in_the_planner():
    assert "if lookback_days > 0 else bar_cap" in SRC


def test_a_negative_value_is_treated_as_off_not_as_negative_bars():
    assert _want(90000, -5, 300) == 90000
