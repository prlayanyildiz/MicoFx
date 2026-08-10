"""The capacity table's cost column needs a reference point, not just a tick.

``cost_pct_of_risk`` is spread+commission as a share of R computed from the
live tick. During the broker rollover FX spreads blow out - measured at 00:23
on this account, AUDUSD read 19x its long-run cost, GBPUSD 16x, EURJPY 10x -
so a healthy symbol looks structurally unprofitable for about half an hour a
day. That is not hypothetical: reading the column without context is what led
to four symbols being switched off on evidence that had evaporated an hour
later.

capacity() now ships the walk-forward's own long-run cost per trade beside
the live one, plus the ratio, so "expensive right now" is distinguishable
from "expensive always".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager


class _Client:
    """Fixed broker: 1 price unit of stop = $10 at 1 lot, spread is the knob."""

    def __init__(self, spread: float) -> None:
        self.spread = spread

    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 100.0, "point": 0.01}

    def resolve(self, symbol):
        return symbol

    def money_per_price_unit(self, symbol, lot):
        return 10.0 * lot

    def min_stop_distance(self, symbol):
        return 0.0

    def normalize_volume(self, symbol, lot):
        return round(lot, 2)

    def margin_for(self, symbol, lot, side):
        return 10.0

    def tick(self, symbol):
        return {"bid": 100.0, "ask": 100.0 + self.spread, "spread": self.spread}


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
        self.system = SystemConfig()
        self.system.size_by_edge = False


def _cfg(typical_cost_r: float | None):
    cfg = SymbolConfig(symbol="EURJPY", magic=1, lot_mode="fixed", fixed_lot=0.1,
                       sl_atr_mult=1.0, commission_per_lot=0.0)
    if typical_cost_r is not None:
        cfg.opt_summary = {"holdout": {"expectancy": 0.23,
                                       "cost_per_trade_r": typical_cost_r}}
    return cfg


def _row(spread: float, typical_cost_r: float | None):
    cfg = _cfg(typical_cost_r)
    rm = RiskManager.__new__(RiskManager)
    rm.store = _Store(cfg)
    rm.client = _Client(spread)
    account = {"equity": 1000.0, "balance": 1000.0, "margin_free": 900.0, "margin": 0.0}
    out = rm.capacity([], account, atr_by_symbol={"EURJPY": 1.0})
    return out["rows"][0]


def test_a_calm_spread_reports_no_inflation():
    # spread 0.05 on a 1.0 stop -> cost share 0.05, typical 0.05 -> 1.0x
    row = _row(spread=0.05, typical_cost_r=0.05)
    assert row["cost_pct_typical"] == pytest.approx(5.0)
    assert row["cost_inflation"] == pytest.approx(1.0, abs=0.15)


def test_a_rollover_spread_is_reported_as_inflated_not_as_the_symbol_s_cost():
    """The real case: live tick 10x the long-run number."""
    row = _row(spread=0.70, typical_cost_r=0.07)
    assert row["cost_pct_of_risk"] > 50.0, "fixture no longer reproduces a blowout"
    assert row["cost_pct_typical"] == pytest.approx(7.0)
    assert row["cost_inflation"] >= 9.0, row["cost_inflation"]


def test_the_typical_cost_survives_a_symbol_with_no_opt_summary():
    """A never-optimised symbol must not crash or invent a reference."""
    row = _row(spread=0.20, typical_cost_r=None)
    assert row["cost_pct_typical"] == 0.0
    assert row["cost_inflation"] == 0.0
    assert row["cost_pct_of_risk"] > 0


def test_a_genuinely_expensive_symbol_still_reads_expensive():
    """The point is context, not excusing cost. High live AND high typical."""
    row = _row(spread=0.40, typical_cost_r=0.38)
    assert row["cost_pct_of_risk"] > 30.0
    assert row["cost_pct_typical"] > 30.0
    assert row["cost_inflation"] < 1.8, "should not be flagged as a passing blowout"


def test_inflation_is_the_ratio_of_the_two_reported_numbers():
    """Whatever the panel shows must be internally consistent."""
    for spread, typical in ((0.05, 0.05), (0.30, 0.06), (0.70, 0.07), (0.12, 0.04)):
        row = _row(spread=spread, typical_cost_r=typical)
        expected = (row["cost_pct_of_risk"] / 100.0) / typical
        assert row["cost_inflation"] == pytest.approx(round(expected, 1), abs=0.11)
