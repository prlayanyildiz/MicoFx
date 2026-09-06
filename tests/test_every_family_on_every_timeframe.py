"""Every strategy family, on every timeframe the book runs, checked as a set.

Families are only ever exercised one at a time, by whichever test needed the
one it was about. That leaves the properties EVERY family has to hold no matter
which one it is - and those are the ones that go wrong quietly, because no
single family's test is the place to notice them.

Five invariants, run over every family in the registry against
M5/M15/M30:

  * it computes at all, on ordinary bars;
  * every series it hands back is the length of the input and free of NaN and
    infinity - a NaN reaching state.atr sizes a position off garbage, which is
    why _try_entry and backtest.simulate both carry an explicit isfinite gate;
  * no look-ahead. Truncating the series must not change any earlier bar's
    signal: bar 300's verdict cannot depend on bar 400 existing. The recursive
    indicators (ema/wilder/T3) seed from src[0], so cutting the END leaves
    their earlier values identical and any difference is the family reading
    forward;
  * a bar never fires buy and sell at once. backtest.simulate refuses that bar
    outright ("a bar that fired both ways trades neither"), so a family
    producing it is silently losing entries rather than erroring;
  * degenerate input does not raise. A flat series - every OHLC identical -
    zeroes ranges, standard deviations and true ranges, which is where the
    divisions live.

The timeframe axis matters because it is not cosmetic here: uses_swing_exits()
switches the exit grid at 900s, htf_t3_trend buckets by wall-clock seconds, and
the scalping families size their entry threshold against per-bar cost. A family
that is fine on M15 is not thereby fine on M30.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.strategy import _FAMILIES, IndicatorCache, Params, compute

FAMILIES = sorted(_FAMILIES)
TIMEFRAMES = {"M5": 300, "M15": 900, "M30": 1800}
N = 900


def _bars(tf_seconds: int, seed: int = 11):
    """A trending random walk with realistic OHLC nesting and a session clock."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 1.0, N) + np.linspace(-0.35, 0.35, N)
    close = 20000.0 + np.cumsum(steps) * 8.0
    open_ = np.concatenate(([close[0]], close[:-1]))
    span = np.abs(rng.normal(0.0, 1.0, N)) * 6.0 + 1.0
    high = np.maximum(open_, close) + span
    low = np.minimum(open_, close) - span
    # Anchored to a real epoch so the session/bucket maths sees ordinary days.
    times = 1_786_000_000 + np.arange(N, dtype=np.int64) * tf_seconds
    volume = rng.integers(50, 5000, N).astype(np.float64)
    cost = np.full(N, 1.2)      # round-turn cost in price units
    return high, low, close, times, open_, volume, cost


def _cache(tf_seconds: int, seed: int = 11, flat: bool = False):
    high, low, close, times, open_, volume, cost = _bars(tf_seconds, seed)
    if flat:
        close = np.full(N, 20000.0)
        open_ = high = low = close.copy()
        volume = np.zeros(N)
        cost = np.zeros(N)
    return IndicatorCache(high, low, close, times, tf_seconds, open_, volume, cost)


def _params(family: str) -> Params:
    # adx_min switches _common from a zeros placeholder onto the real ADX, so
    # the finite/length checks below cover the computed series rather than a
    # stand-in. Left at a value no family treats as a hard filter.
    return Params(strategy=family, adx_min=1.0)


def _series(sig):
    return {"t3": sig.t3, "k": sig.k, "d": sig.d, "atr": sig.atr, "adx": sig.adx,
            "buy": sig.buy, "sell": sig.sell,
            "htf_up": sig.htf_up, "htf_down": sig.htf_down}


CASES = [(f, tf, sec) for f in FAMILIES for tf, sec in TIMEFRAMES.items()]
IDS = [f"{f}-{tf}" for f, tf, _ in CASES]


def test_the_registry_is_the_whole_book():
    """Guards the sweep from silently covering fewer families than exist.

    Fourteen since the six the search never offered were removed - orb,
    vwap_rev, donchian, squeeze_brk, t3_ribbon and liq_sweep. Pinned rather
    than derived so dropping a family stays a deliberate act.
    """
    # 14 -> 12 on 14.08: flow_rev and trix_flip retired on their own record.
    # Across 162 searched candidates neither was ever applied to a symbol and
    # neither was live, and their best holdout score ever was 2.7 and 5.0
    # against a field whose next-worst is 23.2. This number is a tripwire for
    # an ACCIDENTAL change, so it moves only with a reason written beside it.
    # 12 -> 15 on 25.08: alpha_trend, mavilim, ichimoku (Kivanc combo).
    # 15 -> 13 on 26.08: alpha_trend unmeasurable (7 trades < 12), mavilim
    # lost on GER holdout (-20.2 R / PF 0.92). ichimoku passed the same gates.
    # BBW and TD Sequential were measured out of the set: atr_pct_min already
    # gates dead regimes, and TD is a fade counter against an ATR-trail book.
    # 13 -> 11 on 26.08: st_trend and macd_flip never applied (1 and 5
    # searches), neither live, each still paid a full max_combos slot.
    # 11 -> 8 on 27.08: t3_stoch, wavetrend_flip, micro_rev. Retired for
    # SEARCH COST, not a bad holdout - none owned its exit axes, so the
    # shared 6x6x5 product multiplied their grids (t3_stoch to ~1.43e9
    # against a 2000 budget, coverage 0.0001) and none was live.
    # 8 -> 7 on 28.08: aroon_flip. Slowest sweep, worst validated holdout,
    # 1/7 applied, never live; its aroon() indicator went with it.
    # 7 -> 8 on 31.08: channel_break. The first family added on a measured
    # effect rather than a plausible one - favourable MFE/MAE asymmetry in
    # the out-of-sample half of all ten captured windows, growing with
    # lookback rather than spiking at one value (F40).
    # 8 -> 4 on 01.09: stoch_flip, dual_t3, t3_flip, parabolic_flip retired
    # (F39 null forward edge; live book ~-40R on stoch). Leftover DB names
    # fail closed.
    # 4 -> 3 briefly after ichimoku (02.09), then nr_break landed 03.09
    # (keltner rolled back). Same day matrix: nr_break never best on any
    # symbol, roc_pace never best either → live set back to 3
    # (burst / mtf_pullback / channel_break).
    # 3 -> 5 on 04.09: sweep_fade and range_fade joined as DORMANT - present in
    # STRATEGIES, absent from the shipped opt list, so nothing can select them.
    # Named rather than counted: a bare count pin here went red for a reason
    # that had nothing to do with the retirements this file guards.
    assert set(FAMILIES) == {
        "burst", "channel_break", "mtf_pullback", "range_fade", "sweep_fade",
    }, f"aile kitabi degisti: {FAMILIES}"


@pytest.mark.parametrize("family,tf,seconds", CASES, ids=IDS)
def test_it_computes_and_every_series_is_finite(family, tf, seconds):
    sig = compute(_cache(seconds), _params(family))
    for name, arr in _series(sig).items():
        assert arr.size == N, f"{family}/{tf}: {name} uzunlugu {arr.size} != {N}"
        if arr.dtype != bool:
            assert np.all(np.isfinite(arr)), (
                f"{family}/{tf}: {name} icinde NaN/inf var "
                f"({int(np.sum(~np.isfinite(arr)))} bar)")


@pytest.mark.parametrize("family,tf,seconds", CASES, ids=IDS)
def test_no_bar_fires_both_ways(family, tf, seconds):
    sig = compute(_cache(seconds), _params(family))
    both = np.flatnonzero(sig.buy & sig.sell)
    assert both.size == 0, (
        f"{family}/{tf}: {both.size} barda hem al hem sat - backtest bu bari "
        f"tamamen atiyor, yani sessiz giris kaybi")


@pytest.mark.parametrize("family,tf,seconds", CASES, ids=IDS)
def test_an_earlier_bar_does_not_depend_on_a_later_one(family, tf, seconds):
    """Cut the last 120 bars; every remaining bar must decide the same way."""
    full = compute(_cache(seconds), _params(family))
    cut = N - 120
    high, low, close, times, open_, volume, cost = _bars(seconds)
    short = compute(
        IndicatorCache(high[:cut], low[:cut], close[:cut], times[:cut], seconds,
                       open_[:cut], volume[:cut], cost[:cut]),
        _params(family))
    for side in ("buy", "sell"):
        a = getattr(full, side)[:cut]
        b = getattr(short, side)
        drift = np.flatnonzero(a != b)
        assert drift.size == 0, (
            f"{family}/{tf}: {side} sinyali gelecege bakiyor - {drift.size} bar "
            f"degisti, ilki {int(drift[0])}")


@pytest.mark.parametrize("family,tf,seconds", CASES, ids=IDS)
def test_a_flat_market_does_not_raise(family, tf, seconds):
    """Every range, deviation and true range is zero here - where the divisions
    are. Signals are allowed to be anything; crashing is not."""
    sig = compute(_cache(seconds, flat=True), _params(family))
    for name, arr in _series(sig).items():
        if arr.dtype != bool:
            assert np.all(np.isfinite(arr)), f"{family}/{tf}: duz piyasada {name} NaN/inf"
