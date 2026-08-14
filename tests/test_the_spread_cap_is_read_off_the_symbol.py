"""``max_spread_atr`` has to come from the symbol, not from a number we picked.

14.08: the caps were hand-set constants, and the same constant meant different
things on different instruments - 0.12 cut 0.1% of XAUUSD's bars and 77% of
UK100's. Raising them all to a common percentile was the obvious repair and it
was wrong: measured with costs charged, the band it newly admitted returned
-0.126 R on US30 and -0.280 R on UK100.

The reason is legible from the bars alone. Wide-spread bars are not short of
movement - the absolute move over the next eight bars RISES with the spread on
every symbol, by more than the spread costs. What falls is direction:
continuation drops 47.9% -> 45.0% on US30 and 50.1% -> 47.0% on UK100 across the
same buckets. GER40 goes the other way, 49.0% -> 50.2%, and GER40 is the one
symbol whose marginal band measured positive. So the rule is per symbol, and
this is the measurement that decides it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.spread_calibration import (MAX_CAP, MIN_CAP, BandReading,
                                       cap_from_bands, read_bands)


class _Bars:
    def __init__(self, o, h, l, c, s):
        self.open, self.high, self.low, self.close, self.spread = o, h, l, c, s


def _series(n: int, *, trend: float, spread_pts, seed: int = 7) -> _Bars:
    rng = np.random.default_rng(seed)
    step = rng.normal(trend, 1.0, n)
    close = 1000.0 + np.cumsum(step)
    open_ = close - step
    high = np.maximum(open_, close) + 0.5
    low = np.minimum(open_, close) - 0.5
    return _Bars(open_, high, low, close, np.asarray(spread_pts, dtype=float))


def _band(name: str, continuation: float, upper: float,
          net: float = 0.1) -> BandReading:
    return BandReading(name=name, trades=500, upper_ratio=upper,
                       continuation=continuation, net_atr=net)


def test_a_symbol_that_holds_on_both_readings_earns_the_room():
    """The only shape that widens a gate: direction AND net follow-through hold."""
    bands = [_band("p0-p50", 0.490, 0.06, net=0.02),
             _band("p50-p90", 0.494, 0.09, net=0.03),
             _band("p90+", 0.502, 0.19, net=0.04)]
    cap, reason = cap_from_bands(bands, current=0.05)
    assert cap == 0.19, "the widest band still holds, so it sets the ceiling"
    assert "p90+" in reason


def test_a_symbol_that_loses_direction_is_held_where_it_works():
    """US30/UK100's shape: continuation decaying as the spread widens."""
    bands = [_band("p0-p50", 0.479, 0.05),
             _band("p50-p90", 0.477, 0.11),
             _band("p90+", 0.450, 0.31)]
    cap, reason = cap_from_bands(bands, current=0.05)
    assert cap == 0.05, "decay past the cheapest band means no room is earned"
    assert "zayifliyor" in reason


def test_the_walk_stops_at_the_first_failure_not_the_last():
    """A band that recovers past a failed one does not reopen the gate."""
    bands = [_band("p0-p50", 0.500, 0.05),
             _band("p50-p90", 0.440, 0.10),
             _band("p90+", 0.520, 0.40)]
    cap, _ = cap_from_bands(bands, current=0.05)
    assert cap == 0.05, "the ceiling cannot jump a band the symbol cannot trade"


def test_a_symbol_measured_in_one_band_only_is_left_alone():
    """Tightening further would only trade less of the same losing thing."""
    cap, reason = cap_from_bands([_band("p0-p50", 0.40, 0.05)], current=0.12)
    assert cap == 0.12
    assert "cap degismedi" in reason


def test_both_readings_have_to_agree():
    """GER40's real shape: continuation rises, net follow-through decays.

    The first version read continuation alone and opened GER40 and NAS100 on it.
    Cursor's O1 then showed the slope flips with the window and with the horizon,
    while net_atr - what is actually left after paying the spread - decays on
    both. A gate opened on one reading and refused by the other stays shut.
    """
    bands = [_band("p0-p50", 0.490, 0.06, net=-0.015),
             _band("p50-p90", 0.494, 0.09, net=-0.008),
             _band("p90+", 0.502, 0.19, net=-0.075)]
    cap, reason = cap_from_bands(bands, current=0.11)
    assert cap == 0.11, "the qualifying band's ceiling is under the live cap"
    assert "daraltilmadi" in reason


def test_a_reading_never_narrows_a_live_gate():
    """The asymmetry has to be enforced, not just intended.

    A band can qualify on both readings and still have a ceiling below the cap
    already in place - GER40's p50-p90 tops out at 0.09 against a live 0.11.
    Returning it would narrow a gate on a reading only ever trusted to widen one.
    """
    bands = [_band("a", 0.50, 0.04, net=0.1), _band("b", 0.51, 0.09, net=0.2)]
    assert cap_from_bands(bands, current=0.20)[0] == 0.20
    assert cap_from_bands(bands, current=0.05)[0] == 0.09


def test_the_reason_names_which_reading_failed():
    slipped, reason = cap_from_bands(
        [_band("a", 0.50, 0.05, net=0.2), _band("b", 0.50, 0.11, net=0.1)], 0.05)
    assert slipped == 0.05 and "net getiri" in reason
    other, reason2 = cap_from_bands(
        [_band("a", 0.50, 0.05, net=0.1), _band("b", 0.45, 0.11, net=0.2)], 0.05)
    assert other == 0.05 and "yon" in reason2


def test_a_marginal_gain_is_still_a_gain():
    """The rule is the slope, not a level: 47.7 after 47.9 fails, 47.9 holds."""
    fails, _ = cap_from_bands([_band("a", 0.479, 0.05), _band("b", 0.477, 0.11)], 0.05)
    holds, _ = cap_from_bands([_band("a", 0.479, 0.05), _band("b", 0.479, 0.11)], 0.05)
    # net_atr is equal in both, so continuation alone decides this pair.
    assert (fails, holds) == (0.05, 0.11)


def test_no_measurement_never_moves_a_live_cap():
    cap, reason = cap_from_bands([], current=0.08)
    assert cap == 0.08
    assert "olcum yok" in reason


def test_the_cap_stays_inside_its_bounds():
    """0 would disable the gate outright; the top end is past any recorded spread."""
    wide, _ = cap_from_bands([_band("a", 0.50, 0.05), _band("b", 0.50, 9.0)], 0.1)
    assert wide == MAX_CAP
    narrow, _ = cap_from_bands([_band("a", 0.50, 0.00005), _band("b", 0.50, 0.0001)],
                               MIN_CAP / 2)
    assert narrow == MIN_CAP


def test_bands_are_read_off_real_bars():
    """End to end on a trending series: three buckets, ranked by this symbol."""
    n = 3000
    spread = np.concatenate([np.full(n // 2, 2.0), np.full(n - n // 2, 20.0)])
    bands = read_bands(_series(n, trend=0.25, spread_pts=spread), point=0.01)
    assert [b.name for b in bands] == ["p0-p50", "p50-p90", "p90+"]
    assert all(b.trades >= 50 for b in bands)
    assert bands[0].upper_ratio < bands[-1].upper_ratio, "buckets must be ordered"
    assert bands[0].continuation > 0.5, "a trending series must show continuation"


def test_a_series_too_short_to_read_reports_nothing():
    """Better to leave a live cap alone than to set it off forty bars."""
    assert read_bands(_series(60, trend=0.2, spread_pts=np.full(60, 3.0)),
                      point=0.01) == []
