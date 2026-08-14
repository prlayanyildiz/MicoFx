"""Can a symbol pay its own costs?

The cost figure has to be the holdout's ``cost_per_trade_r`` - the same one the
cost gate is measured against, charged only where a signal fired.

The first version of this divided the LIVE instantaneous spread/ATR by
expected_r and read four to five symbols as structurally negative. That was
wrong. web/app.py's portfolio-gates docstring already warned why: an
instantaneous spread/ATR averages every bar while the walk-forward charges only
signal bars, so it runs 5-14x high on short timeframes - and half this book is
M5. It was also sampled at 07:00 with three symbols out of session, the exact
reading #14b calls not-evidence. Measured properly, cost is 17-20% of the edge
on the two symbols that carry a real number, not several times it.

Where the search ran with charge_costs off the holdout figure is 0.0, which
means "never measured", not "free" - so it reports None rather than a
flattering zero.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.models import SymbolConfig


def _engine(cost_per_trade_r, expected_r):
    eng = object.__new__(Engine)
    cfg = SymbolConfig(symbol="SpotBrent")
    cfg.opt_summary = {"holdout": {"cost_per_trade_r": cost_per_trade_r}}
    eng.store = SimpleNamespace(symbols={"SpotBrent": cfg})
    eng.states = {"SpotBrent": SimpleNamespace(
        as_dict=lambda: {"symbol": "SpotBrent", "atr": 0.4})}
    eng.supervisor = SimpleNamespace(
        verdicts={"SpotBrent": SimpleNamespace(expected_r=expected_r)})
    return eng


def test_it_uses_the_holdout_cost_not_the_live_spread():
    """SpotBrent as measured: cost 0.0277 R, edge 0.162 R -> 17% of the edge."""
    row = _engine(0.0277, 0.162)._states_view()["SpotBrent"]

    assert row["cost_r"] == 0.0277
    assert row["edge_cover"] == 0.17, "cost is a fifth of the edge, not several times it"


def test_an_uncharged_search_reports_nothing_rather_than_zero():
    """charge_costs off makes the holdout read 0.0 - that is unmeasured, not free."""
    row = _engine(0.0, 0.162)._states_view()["SpotBrent"]

    assert row["cost_r"] is None
    assert row["edge_cover"] is None


def test_a_cost_above_the_edge_still_reads_over_one():
    """The metric must still be able to say a symbol cannot pay its way."""
    row = _engine(0.20, 0.10)._states_view()["SpotBrent"]

    assert row["edge_cover"] == 2.0


def test_no_expected_edge_reports_none_rather_than_a_fake_ratio():
    row = _engine(0.03, 0.0)._states_view()["SpotBrent"]

    assert row["cost_r"] == 0.03
    assert row["edge_cover"] is None


def test_the_original_state_fields_are_preserved():
    """The view enriches, it must not replace."""
    row = _engine(0.0277, 0.162)._states_view()["SpotBrent"]

    assert row["symbol"] == "SpotBrent"
    assert row["atr"] == 0.4
