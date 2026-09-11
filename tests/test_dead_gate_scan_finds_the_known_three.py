"""The scanner has to catch the three that were found by hand, or it is decor.

Operator, 11.09: "sistemini engelleyen ne varsa tarayin bulun duzeltin veya
kaldirin". Three settings had each silently switched off a whole mechanism
without an error, a failed test or a log line:

  * ``min_positive_ratio`` 0.7 on a six-part ratio - a value the metric cannot
    take, silently meaning 5/6 (83%)
  * ``strategies`` holding 5 of the 7 shipped families
  * ``bad_hour_min_trades`` 80 where the busiest symbol-hour bucket holds 17

The scanner's first run then found a fourth nobody had looked for -
``edge_decay_min_trades`` at 100 against a busiest symbol of 98 - which is the
whole argument for having it.

These tests feed it the historical shapes rather than the live database, so
they keep working after the live values are fixed. A scanner that only passes
because the bugs are still there would be worse than none.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from dead_gate_scan import (  # noqa: E402
    Findings,
    scan_evidence_bars,
    scan_inert_gates,
    scan_lattice,
    scan_overrides,
    scan_search_reach,
)


def _kinds(f: Findings, key: str) -> set[str]:
    return {r["kind"] for r in f.rows if r["key"] == key}


def _autopsies(per_symbol: dict[str, int], hours: int = 6) -> list[dict]:
    """Trades across a handful of hours, recent enough for any lookback.

    hours controls how fat the symbol-hour buckets get: the live book
    spreads 60-98 trades per symbol over the session and its busiest bucket
    holds 17, so six slots reproduces that shape. Spreading the same trades
    over twenty slots makes every bucket too thin and the scanner correctly
    calls even the shipped bar unreachable - which is a fact about the
    fixture, not about the bar.
    """
    import time

    now = time.time()
    rows = []
    for sym, n in per_symbol.items():
        for i in range(n):
            rows.append({"symbol": sym,
                         "exit_time": now - (i % hours) * 3600 - 60,
                         "spread_atr": 0.01 + (i % 5) * 0.005})
    return rows


# ------------------------------------------------------- the three by hand

def test_it_catches_a_ratio_the_metric_cannot_take():
    """Graded by the size of the jump: 0.7 sits a fifth of a step above 4/6
    and is enforced as 5/6, four fifths of a step stricter than typed."""
    f = Findings()
    scan_lattice(f, {"min_positive_ratio": 0.7})
    kinds = _kinds(f, "min_positive_ratio")
    assert kinds == {"STRICTER"}, kinds
    detail = f.rows[0]["detail"]
    assert "5/6" in detail and "83%" in detail, detail


def test_it_catches_a_shipped_family_missing_from_the_search():
    f = Findings()
    scan_overrides(
        f,
        {"strategies": ["burst", "mtf_pullback", "channel_break",
                        "super_trend", "keltner_break"]},
        {"strategies": ["burst", "mtf_pullback", "channel_break",
                        "super_trend", "keltner_break", "range_fade",
                        "sweep_fade"]},
        "opt_params")
    assert _kinds(f, "strategies") == {"OVERRIDE"}
    assert "range_fade" in f.rows[0]["detail"]


def test_it_catches_an_hour_bar_no_bucket_can_reach():
    f = Findings()
    scan_evidence_bars(f, {"bad_hour_min_trades": 80},
                       _autopsies({"GER40": 60, "US30": 98}), 30.0)
    assert "DEAD" in _kinds(f, "bad_hour_min_trades")


def test_it_catches_the_fourth_it_found_on_its_own():
    """edge_decay_min_trades 100 against a busiest symbol of 98."""
    f = Findings()
    scan_evidence_bars(f, {"edge_decay_min_trades": 100},
                       _autopsies({"GER40": 60, "US30": 98}), 30.0)
    assert "DEAD" in _kinds(f, "edge_decay_min_trades")


# ------------------------------------------------ the other two directions

def test_it_catches_a_gate_that_never_refuses_anything():
    f = Findings()
    scan_inert_gates(f, [{"symbol": "XAUUSD", "max_spread_atr": 0.25}],
                     [{"symbol": "XAUUSD", "spread_atr": 0.0144},
                      {"symbol": "XAUUSD", "spread_atr": 0.0339}])
    assert "INERT" in _kinds(f, "max_spread_atr")


def test_it_catches_a_live_value_the_search_can_never_restore():
    f = Findings()
    scan_search_reach(f, {"grid": {"max_spread_atr": [0.01, 0.05, 0.15]}},
                      [{"symbol": "XAUUSD", "max_spread_atr": 0.25}])
    assert "CEILING" in _kinds(f, "max_spread_atr")


# ------------------------------------------------------ and stays quiet otherwise

def test_a_healthy_configuration_reports_nothing():
    f = Findings()
    scan_lattice(f, {"min_positive_ratio": 4 / 6})
    scan_overrides(f, {"max_combos": 2000}, {"max_combos": 2000}, "opt_params")
    scan_evidence_bars(f, {"bad_hour_min_trades": 6, "min_trades": 25},
                       _autopsies({"GER40": 60, "US30": 98}), 30.0)
    scan_inert_gates(f, [{"symbol": "GER40", "max_spread_atr": 0.05}],
                     [{"symbol": "GER40", "spread_atr": 0.03},
                      {"symbol": "GER40", "spread_atr": 0.0695}])
    scan_search_reach(f, {"grid": {"max_spread_atr": [0.01, 0.05, 0.15]}},
                      [{"symbol": "GER40", "max_spread_atr": 0.05}])
    assert f.rows == [], f.rows


def test_a_rounded_but_reachable_bar_is_not_called_dead():
    """0.6 also sits between rungs and means 4/6 - misleading, not fatal.
    Calling that DEAD would bury the real ones in noise."""
    f = Findings()
    scan_lattice(f, {"min_positive_ratio": 0.6})
    assert _kinds(f, "min_positive_ratio") == {"ROUNDED"}
