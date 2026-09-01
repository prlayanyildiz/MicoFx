"""The measured tick/bar gap has to reach the search, or measuring it is theatre.

simulate() charges and gates on the entry BAR's spread; engine._try_entry
gates on the CURRENT TICK's, which runs wider. walk_forward now scales its
spread series by the engine's measured median for that symbol, so the ceiling
the search picks is one live can actually clear.

Deliberately inert until there is evidence: the scale is 1.0 - the previous
behaviour exactly - until a symbol has cleared SPREAD_RATIO_MIN_SAMPLES, and
it is clamped at 1.0 from below so a sub-1 reading can never make the search
cheerier than the bars justify. The upper bound is the histogram's own
maximum: an earlier 3.0 was picked before any data existed and turned out to
sit BELOW the highest real measurement (CHFJPY, 3.35 over 3204 samples),
clipping the one symbol the whole mechanism was built for.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest as bt
from micofx.engine import SPREAD_RATIO_BUCKETS, SPREAD_RATIO_MIN_SAMPLES, SPREAD_RATIO_STEP
from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Bars:
    def __init__(self, n=3000, spread=30.0):
        rng = np.random.default_rng(11)
        t = np.arange(n)
        step = rng.normal(0.0, 0.35, n) + 0.02 * np.sin(t / 40.0) + t * 0.001
        close = (100 + np.cumsum(step)).astype(np.float64)
        self.close = close
        open_ = np.empty_like(close)
        open_[0] = close[0]
        open_[1:] = close[:-1]
        self.open = open_
        hi = np.maximum(open_, close) + np.abs(rng.normal(0.25, 0.1, n))
        lo = np.minimum(open_, close) - np.abs(rng.normal(0.25, 0.1, n))
        self.high = hi
        self.low = lo
        self.volume = np.full(n, 100.0)
        self.spread = np.full(n, spread)
        self.time = (np.arange(n) * 300 + 1_700_000_000).astype(np.int64)

    def __len__(self):
        return self.close.size


GRID = {"chan_lookback": [20, 40, 60, 100],
        "sl_atr_mult": [1.5, 2.0, 2.5, 3.0, 4.0],
        "trail_start_atr": [1.0, 2.0],
        "trail_step_atr": [1.0, 2.0]}

# channel_break on a trending random-walk fixture: charged cost rises linearly
# with spread_scale — the property under test. The family name is explicit
# because the dataclass default moved when flip families retired.
def _run(**kw):
    args = {"cfg": SymbolConfig(symbol="FRA40", magic=1, strategy="channel_break",
                                use_sessions=False),
            "bars": _Bars(), "point": 1e-4, "tf_seconds": 300, "grid": GRID,
            "min_trades": 5, "segments": 4, "max_combos": 48,
            "min_positive_ratio": 0.0, "refine_rounds": 0, "plateau_weight": 0.0}
    args.update(kw)
    return bt.walk_forward(**args)


def _cost(result):
    return float(((result.get("best") or {}).get("selection") or {})
                 .get("cost_per_trade_r") or 0.0)


# ------------------------------------------------- the search sees the gap

def test_scaling_the_spread_raises_the_cost_the_search_charges():
    base = _run(spread_scale=1.0)
    wide = _run(spread_scale=2.0)
    assert base.get("ok") and wide.get("ok"), (base.get("error"), wide.get("error"))
    assert _cost(wide) > _cost(base) * 1.5, (_cost(base), _cost(wide))


def test_the_default_changes_nothing():
    """Every existing caller must get exactly the old numbers."""
    plain = _run()
    explicit = _run(spread_scale=1.0)
    assert _cost(plain) == _cost(explicit)
    assert plain.get("ok") == explicit.get("ok")


@pytest.mark.parametrize("scale", [0.0, -1.0, None])
def test_a_meaningless_scale_falls_back_to_one(scale):
    assert _cost(_run(spread_scale=scale)) == _cost(_run(spread_scale=1.0))


def test_a_scaled_run_can_refuse_what_an_unscaled_one_accepted():
    """The point of the exercise: configs that only work at unreal spreads."""
    wide = _run(spread_scale=3.0, max_cost_share=0.10)
    base = _run(spread_scale=1.0, max_cost_share=0.10)
    assert base.get("ok"), base.get("error")
    assert (not wide.get("ok")) or _cost(wide) > _cost(base)


# --------------------------------------------- the lookup that feeds it

class _Store:
    def __init__(self, blob=None):
        self.saved = {"spread_ratio": blob} if blob is not None else {}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)


def _optimizer(blob=None):
    opt = object.__new__(Optimizer)
    opt.store = _Store(blob)
    return opt


def _hist(bucket, count):
    counts = [0] * SPREAD_RATIO_BUCKETS
    counts[bucket] = count
    return counts


def test_no_measurement_leaves_the_search_untouched():
    assert _optimizer()._spread_scale("FRA40") == 1.0
    assert _optimizer({})._spread_scale("FRA40") == 1.0


def test_a_thin_sample_leaves_the_search_untouched():
    blob = {"FRA40": _hist(20, SPREAD_RATIO_MIN_SAMPLES - 1)}
    assert _optimizer(blob)._spread_scale("FRA40") == 1.0


def test_a_measured_symbol_gets_its_median():
    blob = {"FRA40": _hist(20, SPREAD_RATIO_MIN_SAMPLES)}   # ratios in [2.0, 2.1)
    assert _optimizer(blob)._spread_scale("FRA40") == pytest.approx(2.05, abs=0.01)


def test_a_ratio_below_one_never_makes_the_search_cheerier():
    blob = {"GBPUSD": _hist(5, SPREAD_RATIO_MIN_SAMPLES)}   # ratios in [0.5, 0.6)
    assert _optimizer(blob)._spread_scale("GBPUSD") == 1.0


@pytest.mark.parametrize("blob", [
    {"X": "bozuk"}, {"X": None}, {"X": [1, 2, 3]}, {"X": {"a": 1}},
    {"X": [None] * SPREAD_RATIO_BUCKETS}, "hic dict degil",
])
def test_a_corrupt_histogram_never_disturbs_a_search(blob):
    assert _optimizer(blob)._spread_scale("X") == 1.0


def test_an_unmeasured_symbol_in_a_populated_blob_is_untouched():
    blob = {"FRA40": _hist(20, SPREAD_RATIO_MIN_SAMPLES)}
    assert _optimizer(blob)._spread_scale("XAUUSD") == 1.0


# ------------------------------------------------ the ceiling is a sanity bound

def test_the_highest_measured_symbol_is_not_truncated():
    """CHFJPY measures 3.35 over 3204 samples. A 3.0 ceiling was not catching
    an absurd reading, it was clipping the one measurement that matters most
    and searching the book's most expensive symbol ~10% cheaper than it is."""
    blob = {"CHFJPY": _hist(33, SPREAD_RATIO_MIN_SAMPLES)}   # ratios in [3.3, 3.4)
    assert _optimizer(blob)._spread_scale("CHFJPY") == pytest.approx(3.35, abs=0.01)


def test_the_ceiling_is_the_histograms_own_maximum():
    """The last bucket is an overflow reported at its lower edge, so 5.0 is
    the highest median that can exist. The ceiling is the measurement's
    resolution, not a number chosen here - which is what stops it clipping
    real data the way the first 3.0 did."""
    blob = {"X": _hist(SPREAD_RATIO_BUCKETS - 1, SPREAD_RATIO_MIN_SAMPLES)}
    assert _optimizer(blob)._spread_scale("X") == 5.0
    assert (SPREAD_RATIO_BUCKETS - 1) * SPREAD_RATIO_STEP == pytest.approx(5.0)


def test_the_floor_still_refuses_to_make_the_search_cheerier():
    """The one direction the whole mechanism exists to prevent."""
    for bucket in (0, 5, 9):
        blob = {"X": _hist(bucket, SPREAD_RATIO_MIN_SAMPLES)}
        assert _optimizer(blob)._spread_scale("X") == 1.0


def test_the_sample_threshold_is_what_guards_against_a_glitch():
    """A frozen feed cannot hold a stable median across the threshold; below
    it nothing is applied at all, whatever the reading says."""
    blob = {"X": _hist(SPREAD_RATIO_BUCKETS - 1, SPREAD_RATIO_MIN_SAMPLES - 1)}
    assert _optimizer(blob)._spread_scale("X") == 1.0


def test_a_store_failure_returns_one_but_says_so_once():
    """Same class as the engine flush latch: 1.0 keeps the search running,
    silence lets a frozen sqlite look like 'no measurement' and cost ~10% cheap.
    One WARN, then quiet until a successful read re-arms it.
    """
    from micofx.logbus import LOG

    class _Boom:
        def get_setting(self, key, default=None):
            raise OSError("disk")

    opt = object.__new__(Optimizer)
    opt.store = _Boom()
    seen: list[tuple[str, str, str]] = []
    orig = LOG.emit

    def _cap(msg, level="INFO", symbol=""):
        seen.append((msg, level, symbol))
        return orig(msg, level, symbol)

    LOG.emit = _cap
    try:
        assert opt._spread_scale("XAUUSD") == 1.0
        assert opt._spread_scale("XAUUSD") == 1.0
        warns = [row for row in seen if row[1] == "WARN"]
        assert len(warns) == 1
        assert "spread_ratio" in warns[0][0]
        assert warns[0][2] == "XAUUSD"

        opt.store = _Store({"XAUUSD": _hist(20, SPREAD_RATIO_MIN_SAMPLES)})
        measured = opt._spread_scale("XAUUSD")
        assert measured > 1.0
        opt.store = _Boom()
        seen.clear()
        assert opt._spread_scale("XAUUSD") == 1.0
        assert len([row for row in seen if row[1] == "WARN"]) == 1
    finally:
        LOG.emit = orig
