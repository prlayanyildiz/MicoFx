"""The cost-regime stamp must describe the sweep, not the wall clock.

``opt_summary["charge_costs"]`` exists so a score earned with the spread zeroed
is never compared, as though like for like, against one earned while costs were
charged - the cost-free number is the larger of the two, so without the stamp a
cost-free incumbent can never be beaten and the symbol freezes on it.

It was read off ``store.system`` at the moment the row was written, which is a
different question from the one it claims to answer. Found 14.08: the full
ten-symbol run started 20:10:40 with ``charge_costs`` still False, the flag went
True at 20:13:13, and SpotBrent's row landed at 20:17:41 stamped **True** beside
``cost_r 0.0`` over 1532 holdout trades. The stamp said charged; the sweep had
filled at the printed price. A stamp that can lie is worse than no stamp.

So it now travels with the numbers: ``walk_forward`` reports the regime it ran
under, and ``apply`` records that instead of asking the store again.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


class _System:
    def __init__(self, charge_costs: bool) -> None:
        self.charge_costs = charge_costs


class _Store:
    def __init__(self, charge_costs: bool) -> None:
        self.system = _System(charge_costs)


def _stamp(detail: dict, store_says: bool) -> bool:
    """Rebuild the one expression under test, bound off the real class."""
    opt = Optimizer.__new__(Optimizer)
    opt.store = _Store(store_says)
    value = detail.get("charge_costs")
    return (bool(detail["charge_costs"]) if value is not None
            else bool(getattr(getattr(opt.store, "system", None),
                              "charge_costs", True)))


def test_a_cost_free_sweep_is_not_relabelled_by_a_later_flip():
    """The exact 14.08 sequence: sweep ran cost-free, flag flipped mid-run."""
    assert _stamp({"charge_costs": False}, store_says=True) is False


def test_a_charged_sweep_is_not_relabelled_either():
    """The same hazard in the other direction, if the flag is switched off."""
    assert _stamp({"charge_costs": True}, store_says=False) is True


def test_an_old_result_without_the_field_falls_back_to_the_store():
    """Rows produced before walk_forward reported it must still record something."""
    assert _stamp({"holdout_days": 36.5}, store_says=True) is True
    assert _stamp({"holdout_days": 36.5}, store_says=False) is False


def test_the_sweep_reports_the_regime_it_ran_under():
    """walk_forward is the only place that knows; it has to say so."""
    import inspect

    from micofx import backtest

    src = inspect.getsource(backtest.walk_forward)
    assert '"charge_costs": bool(charge_costs)' in src, (
        "the report must carry the regime out with the numbers it produced")
    assert '"spread_scale": float(scale)' in src


def test_apply_receives_it_from_the_report():
    """The value has to survive the hop from walk_forward to apply()."""
    import inspect

    from micofx import optimizer

    src = inspect.getsource(optimizer.Optimizer.run_symbol
                            if hasattr(optimizer.Optimizer, "run_symbol")
                            else optimizer.Optimizer)
    assert '"charge_costs": report.get("charge_costs")' in src, (
        "apply() cannot stamp what the caller never handed it")
    assert '"spread_scale": report.get("spread_scale")' in src, (
        "spread_scale has the same clock-vs-measurement hazard")
