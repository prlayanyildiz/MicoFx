"""Zero-spread history bars must not be priced as free.

AV1 / GER40 M30: 21581 of 90000 bars record spread 0, and the first 20%
are entirely empty. That is a quote hole, not a market that charged
nothing. walk_forward used bars.spread raw, so a quarter of the window
paid 0 and the search picked a max_spread_atr under the live quote.

Found on the 2026-08-16 account pull. Median of the bars that do quote
fills the hole; dropping them would rewrite the walk-forward windows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest as bt


def test_zero_quotes_are_replaced_with_the_symbols_median():
    pts = np.array([0.0, 10.0, 0.0, 20.0])
    got = bt.imputed_spread_pts(pts)
    assert list(got) == [15.0, 10.0, 15.0, 20.0]


def test_an_all_quoted_series_is_unchanged():
    pts = np.array([8.0, 12.0, 10.0])
    assert np.array_equal(bt.imputed_spread_pts(pts), pts)


def test_the_search_and_the_charged_replay_both_impute():
    """A helper nobody calls is the same as no fix."""
    wf = (Path(__file__).resolve().parents[1] / "micofx" / "backtest.py"
          ).read_text(encoding="utf-8")
    slice_src = (Path(__file__).resolve().parents[1] / "micofx" / "holdout_cost.py"
                 ).read_text(encoding="utf-8")
    assert "spread_cost_series(" in wf
    assert "bars.spread" in wf
    assert "spread_cost_series(" in slice_src
