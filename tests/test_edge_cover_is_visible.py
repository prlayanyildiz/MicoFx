"""Can a symbol pay its own spread?

``expected_r`` (the holdout's edge per trade) lived on the supervisor verdict
and the live spread lived on the symbol state, so the one comparison that
answers this needed a manual three-way join. Measured that way on 14.08:

    expected edge  0.058-0.212 R/trade   vs   spread  0.02-0.18 R/trade

Five of ten symbols carried a spread at or above their entire expected edge -
structurally negative before a tick moves - and nothing surfaced it.

The existing cost gate does not catch this by construction: it measures cost
against R, and R is 5-20x the edge here, so a trade costing 17% of R clears an
18% gate while spending more than twice what it expects to make.

Reported, not enforced: what to do about it is a book decision (#30).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.models import SymbolConfig


def _engine(atr, spread, sl_mult, expected_r):
    eng = object.__new__(Engine)
    cfg = SymbolConfig(symbol="UK100", sl_atr_mult=sl_mult)
    eng.store = SimpleNamespace(symbols={"UK100": cfg})
    eng.states = {"UK100": SimpleNamespace(
        atr=atr, spread=spread,
        as_dict=lambda: {"symbol": "UK100", "atr": atr, "spread": spread})}
    eng.supervisor = SimpleNamespace(
        verdicts={"UK100": SimpleNamespace(expected_r=expected_r)})
    return eng


def test_a_symbol_whose_spread_exceeds_its_edge_reads_over_one():
    """UK100 as measured: edge 0.108 R, spread 0.181 R."""
    row = _engine(atr=10.0, spread=1.81, sl_mult=1.0, expected_r=0.108)._states_view()["UK100"]

    assert row["cost_r"] == 0.181
    assert row["edge_cover"] > 1.0, "spread above the whole edge must read as short"
    assert row["edge_cover"] == 1.68


def test_a_symbol_that_covers_its_costs_reads_below_one():
    """XAUUSD as measured: edge 0.093 R, spread 0.020 R."""
    row = _engine(atr=10.0, spread=0.20, sl_mult=1.0, expected_r=0.093)._states_view()["UK100"]

    assert row["edge_cover"] < 1.0
    assert row["edge_cover"] == 0.22


def test_no_expected_edge_yet_reports_none_rather_than_a_fake_ratio():
    """A symbol with no holdout must not read as infinitely healthy or broken."""
    row = _engine(atr=10.0, spread=1.0, sl_mult=1.0, expected_r=0.0)._states_view()["UK100"]

    assert row["cost_r"] == 0.1
    assert row["edge_cover"] is None


def test_a_missing_atr_does_not_divide_by_zero():
    row = _engine(atr=0.0, spread=1.0, sl_mult=1.0, expected_r=0.1)._states_view()["UK100"]

    assert row["cost_r"] == 0.0
    assert row["edge_cover"] == 0.0


def test_the_original_state_fields_are_preserved():
    """The view enriches, it must not replace."""
    row = _engine(atr=10.0, spread=1.0, sl_mult=1.0, expected_r=0.1)._states_view()["UK100"]

    assert row["symbol"] == "UK100"
    assert row["atr"] == 10.0
