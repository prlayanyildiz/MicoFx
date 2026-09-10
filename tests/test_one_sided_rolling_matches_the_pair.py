"""``rolling_max`` / ``rolling_min`` must equal the half of the pair they replace.

Both breakout families asked for the pair twice and discarded half of each
answer:

    _, hi = rolling_min_max(cache.high, window)
    lo, _ = rolling_min_max(cache.low, window)

Four windowed reductions over 90,000 bars to use two. They call the one-sided
helpers now, which is only safe while the values are bit-identical - a signal
series that shifts by one ULP moves an entry bar, and every stored holdout
number was measured on the old one.

The pair function stays: stoch needs both sides of one series.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.indicators as ind

WINDOWS = (1, 2, 3, 5, 14, 20, 50, 120, 400)


def test_one_sided_equals_the_pair_exactly():
    rng = np.random.default_rng(3)
    for _ in range(200):
        src = rng.normal(100.0, 5.0, int(rng.integers(0, 300))).astype(np.float64)
        for w in WINDOWS:
            lo, hi = ind.rolling_min_max(src, w)
            assert np.array_equal(ind.rolling_max(src, w), hi, equal_nan=True), (w, src.size)
            assert np.array_equal(ind.rolling_min(src, w), lo, equal_nan=True), (w, src.size)


def test_the_warmup_head_is_expanding_not_padded():
    """Before a full window exists the value is the running extreme, not NaN
    and not the first bar repeated - a padded head would move the first
    entries of every breakout family."""
    src = np.array([5.0, 3.0, 9.0, 1.0, 7.0])
    assert list(ind.rolling_max(src, 3)) == [5.0, 5.0, 9.0, 9.0, 9.0]
    assert list(ind.rolling_min(src, 3)) == [5.0, 3.0, 3.0, 1.0, 1.0]


def test_an_empty_series_is_empty_not_an_error():
    empty = np.array([], dtype=np.float64)
    assert ind.rolling_max(empty, 5).size == 0
    assert ind.rolling_min(empty, 5).size == 0


def test_a_window_longer_than_the_series_stays_expanding():
    src = np.array([2.0, 8.0, 4.0])
    assert list(ind.rolling_max(src, 50)) == [2.0, 8.0, 8.0]
    assert list(ind.rolling_min(src, 50)) == [2.0, 2.0, 2.0]


def test_the_breakout_families_no_longer_ask_for_both_sides():
    """Guard the saving: a reverted call site would double the work back and
    nothing else would notice."""
    src_text = (Path(ind.__file__).parent / "strategy.py").read_text(encoding="utf-8")
    assert "_, hi = ind.rolling_min_max" not in src_text
    assert "lo, _ = ind.rolling_min_max" not in src_text
    assert "ind.rolling_max(" in src_text
    assert "ind.rolling_min(" in src_text
