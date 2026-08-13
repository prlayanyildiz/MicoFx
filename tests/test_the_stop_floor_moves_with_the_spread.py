"""The trail was allowed to hug price in a way live never can.

``mt5client.min_stop_distance`` is ``max(stops_level, spread * 1.5, point*10)``,
so the floor under any stop **moves with the spread**. The engine recomputes it
on every trail check. The optimizer read it once, at plan time, and passed that
single number through a walk-forward covering months of bars.

A sweep planned in a quiet minute therefore gave the simulation a small floor
and let its trail sit closer to price than the broker would ever allow. The
error runs one way: a trail that hugs closer gives back less on the reversal
that ends the trade, which inflates exactly the winners the reward ratio is
built from. Live reward ratio is 1.05 against a paper 3.43.

The floor is now rebuilt per bar from that bar's own recorded spread.

It is built from the RAW bar spread, deliberately not from ``spread_price``.
That series is zeroed when ``charge_costs`` is off, and this is not a cost - a
stop cannot sit inside the spread whatever the accounting says. The two must
stay separate or switching costs off would quietly hand the trail a floor of
zero and make the same optimism worse.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKTEST = (Path(__file__).resolve().parents[1] / "micofx" / "backtest.py").read_text(
    encoding="utf-8")


def _series(spread_pts, point, plan_floor):
    """The two lines under test, reproduced from walk_forward."""
    raw = np.asarray(spread_pts, dtype=np.float64) * point
    const = float(plan_floor) if plan_floor else (point * 10.0)
    return np.maximum(const, raw * 1.5)


# ------------------------------------------------------------- the defect

def test_the_floor_follows_each_bar_rather_than_one_snapshot():
    quiet, wide = 2.0, 40.0
    s = _series([quiet, wide], point=0.1, plan_floor=0.3)
    assert s[0] != s[1], "taban hala tek bir sayi - genis spread bari kelepcelenmiyor"
    assert s[1] > s[0]


def test_a_wide_bar_lifts_the_floor_above_the_plan_time_value():
    """The case that produced the optimism: planned quiet, traded wide."""
    s = _series([50.0], point=0.1, plan_floor=0.3)
    assert s[0] > 0.3


def test_walk_forward_builds_it_from_the_raw_spread_not_the_cost_series():
    """spread_price is zeroed by charge_costs; this must not be."""
    assert "raw_spread_price = bars.spread * point" in BACKTEST
    raw = BACKTEST.index("raw_spread_price = bars.spread * point")
    zero = BACKTEST.index("spread_price = np.zeros_like(spread_price)")
    assert raw < zero, "taban serisi maliyet sifirlamasindan SONRA kuruluyor"
    block = BACKTEST[raw:zero]
    assert "min_stop_series = np.maximum(" in block


def test_simulate_takes_the_series_and_reads_it_per_bar():
    assert "min_stop=min_stop_series," in BACKTEST
    assert "float(min_stop_at[j0])" in BACKTEST, "giris stopu bar tabanini okumuyor"
    assert "ms = float(min_stop_at[j])" in BACKTEST, "trail bar tabanini okumuyor"


# --------------------------------------------------- what must keep working

def test_the_stops_level_part_is_still_a_floor():
    """A quiet bar must not drop below what the broker demands regardless."""
    s = _series([0.0, 1.0], point=0.1, plan_floor=0.5)
    assert s[0] == 0.5
    assert s[1] == 0.5


def test_a_caller_passing_a_plain_number_still_works():
    """simulate is called directly in places that have no series."""
    assert "min_stop if isinstance(min_stop, np.ndarray)" in BACKTEST
    assert "np.full(open_.size, float(min_stop)" in BACKTEST


def test_the_default_is_still_ten_points():
    assert "min_stop = point * 10.0" in BACKTEST
