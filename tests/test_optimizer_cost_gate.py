"""The search must not propose configs the live entry gate will refuse.

engine._try_entry refuses any entry whose spread+commission exceeds
system.max_cost_pct_of_risk of that trade's R. The simulator has always
measured the same drag (Result.cost_r) but nothing used it to reject a
candidate, so the search could rank a tight-stop config whose cost ate most
of the risk - and live then refused every entry it produced. That is how a
symbol ends up with one or two live trades while its backtest summary looks
healthy.

walk_forward now screens candidates on the same ceiling, expressed as a
share of R rather than a percentage.

The fixture is a rising series with regular pullbacks, which channel_break can
actually trade - a random walk yields no winning candidate at all, so the
cost gate would never be reached and the assertions would pass vacuously.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.models import SymbolConfig

N = 6000
TF = 300
# What this fixture's winner actually costs per trade, in R, at spread 20.
# Pinned by test_the_fixture_costs_what_these_thresholds_assume below so the
# thresholds here cannot silently stop meaning anything.
# Re-measured 27.08 when t3_stoch retired. The bars are unchanged; the stop
# grid widened because no surviving family clears a 0.5-ATR stop against this
# fixture's spread. What the file measures - that max_cost_share filters on
# cost/R - is unchanged, and test_the_fixture_costs_what_these_thresholds_assume
# below still guards the relationship.
FIXTURE_COST_R = 0.123


class _Bars:
    """Stand-in for the real Bars: walk_forward calls len() on it."""

    def __init__(self, close, spread_points):
        self.time = np.arange(N, dtype=np.int64) * TF
        self.spread = np.full(N, spread_points, dtype=float)
        self.volume = np.ones(N)
        self.close = close
        self.high = close + 0.4
        self.low = close - 0.4
        self.open = np.concatenate([[close[0]], close[:-1]])

    def __len__(self):
        return N


def _bars(spread_points: float = 20.0):
    rng = np.random.default_rng(3)
    t = np.arange(N)
    close = 100.0 + t * 0.01 + 3.0 * np.sin(t / 40.0) + rng.normal(0, 0.15, N)
    return _Bars(close, spread_points)


def _cfg():
    return SymbolConfig(symbol="TEST", magic=1, timeframe="M5", strategy="channel_break",
                        use_sessions=False)


GRID = {"sl_atr_mult": [1.0, 2.0, 3.0], "trail_start_atr": [1.0, 2.0],
        "trail_step_atr": [1.0, 2.0], "chan_lookback": [20, 40, 60]}


def _run(max_cost_share: float, spread_points: float = 20.0):
    return backtest.walk_forward(
        _cfg(), _bars(spread_points), point=0.01, tf_seconds=TF, grid=GRID,
        min_trades=5, segments=5, max_combos=60, min_positive_ratio=0.0,
        plateau_weight=0.0, refine_rounds=0, max_cost_share=max_cost_share)


def test_the_fixture_costs_what_these_thresholds_assume():
    """Guard the fixture: every threshold below is stated relative to this."""
    out = _run(max_cost_share=0.0)
    assert out.get("ok"), "fixture artik kazanan aday uretmiyor"
    cost = out["best"]["selection"]["cost_per_trade_r"]
    assert cost == pytest.approx(FIXTURE_COST_R, abs=0.01), cost


def test_an_unfiltered_search_still_wins(  ):
    """max_cost_share = 0 means the live gate is off - behave exactly as before."""
    out = _run(max_cost_share=0.0)
    assert out.get("ok")
    assert out.get("rejected_costly") == 0


def test_a_ceiling_below_the_candidate_s_cost_rejects_it():
    """The headline behaviour: too expensive to trade means it cannot win."""
    out = _run(max_cost_share=FIXTURE_COST_R / 2)
    assert out.get("rejected_costly", 0) > 0, "pahali aday elenmedi"
    if out.get("ok"):
        # If something else survived, it has to be inside the ceiling.
        assert out["best"]["selection"]["cost_per_trade_r"] <= FIXTURE_COST_R / 2 + 1e-9


def test_a_ceiling_above_the_candidate_s_cost_admits_it():
    """The gate must not reject what live would happily trade."""
    out = _run(max_cost_share=FIXTURE_COST_R * 2)
    assert out.get("ok")
    assert out.get("rejected_costly") == 0
    assert out["best"]["selection"]["cost_per_trade_r"] <= FIXTURE_COST_R * 2


def test_the_winner_always_respects_the_ceiling():
    """Stated directly, across a range: nothing above the limit ever wins."""
    for ceiling in (0.05, 0.10, 0.20, 0.50, 1.0):
        out = _run(max_cost_share=ceiling)
        if not out.get("ok"):
            continue
        cost = out["best"]["selection"]["cost_per_trade_r"]
        assert cost <= ceiling + 1e-9, f"tavan {ceiling}, kazanan {cost}"


def test_tightening_the_ceiling_never_admits_more():
    """Monotonic: a stricter limit cannot accept what a looser one rejected."""
    loose = _run(max_cost_share=1.0)
    strict = _run(max_cost_share=0.05)
    assert strict.get("rejected_costly", 0) >= loose.get("rejected_costly", 0)


def test_a_wider_spread_costs_more_and_is_gated_sooner():
    """Ties the gate to the thing it is actually about - the real spread."""
    cheap = _run(max_cost_share=0.0, spread_points=2.0)
    dear = _run(max_cost_share=0.0, spread_points=40.0)
    if cheap.get("ok") and dear.get("ok"):
        assert (cheap["best"]["selection"]["cost_per_trade_r"]
                < dear["best"]["selection"]["cost_per_trade_r"])
