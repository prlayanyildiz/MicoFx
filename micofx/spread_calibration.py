"""Set each symbol's ``max_spread_atr`` from its own behaviour, not from a number.

The gate used to be a hand-set constant, and the same constant meant different
things on different symbols: 0.12 cut 0.1% of XAUUSD's bars and 77% of UK100's.
Widening them all to a common percentile was the obvious repair and it was wrong
- measured with costs charged, the newly admitted band returned -0.126 R on US30
and -0.280 R on UK100, against +0.120 and +0.263 below the old cap.

Wide-spread bars are not short of movement. Bucketed by spread rank, the absolute
move over the next eight bars RISES with the spread on every symbol in the book,
and rises by more than the spread costs. What falls is the *direction*: the share
of bars whose own direction still holds eight bars later drops from 47.9% to
45.0% on US30, 50.1% to 47.0% on UK100, 48.1% to 45.9% on SpotBrent. More motion,
less of it one-way - which is what a trend-following family cannot use.

GER40 is the exception on both counts: continuation 49.0% -> 50.2% across the
same bands, and it is the one symbol whose marginal band measured POSITIVE
(+0.153 R). So the answer is per symbol, and it is legible from the bars alone -
no strategy, no backtest, no cost model. That is what this module reads.

It exists as a separate calibration rather than another search dimension because
``max_spread_atr`` already IS one: with ``charge_costs`` on, the sweep would
price the band and pick the cap itself. Under the operator's decision of 14.08
the sweep does not charge the spread, so it cannot see what a looser cap costs
and would always take the loosest. This measures it on the side, where the flag
does not reach.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Eight bars is the book's own holding period: the applied configs report an
# average of 7.6 bars per trade across the holdout.
HORIZON_BARS = 8
ATR_PERIOD = 14

# A band has to hold its direction at least this well to be worth admitting.
# Below a coin flip the family is paying the spread for the privilege of being
# wrong slightly more often than right.
MIN_CONTINUATION = 0.485

# Never propose a cap outside this range whatever the bars say: 0 would disable
# the gate entirely and the upper end is past any spread the book has recorded.
MIN_CAP, MAX_CAP = 0.03, 0.50


@dataclass
class BandReading:
    """One spread bucket's record."""

    name: str
    trades: int
    upper_ratio: float          # the spread/ATR ceiling this band reaches
    continuation: float         # share of bars whose direction still holds
    net_atr: float              # signed follow-through minus the spread paid


@dataclass
class Calibration:
    symbol: str
    timeframe: str
    bands: list[BandReading]
    cap: float
    reason: str


def _atr(high, low, close, period: int = ATR_PERIOD):
    tr = np.maximum(high[1:] - low[1:],
                    np.maximum(np.abs(high[1:] - close[:-1]),
                               np.abs(low[1:] - close[:-1])))
    return np.convolve(tr, np.ones(period) / period, mode="valid")


def read_bands(bars, point: float, percentiles=(50.0, 90.0)) -> list[BandReading]:
    """Bucket the bars by spread rank and report each bucket's follow-through.

    ``bars`` is anything with open/high/low/close/spread arrays - the same shape
    ``backtest`` takes. Ranks are the symbol's own, so a band means the same
    thing everywhere: "the cheapest half of this symbol's conditions", not a
    number that happens to be small on one instrument and huge on another.
    """
    high, low = np.asarray(bars.high), np.asarray(bars.low)
    close, open_ = np.asarray(bars.close), np.asarray(bars.open)
    spread = np.asarray(bars.spread, dtype=float)

    atr = _atr(high, low, close)
    start = ATR_PERIOD
    n = len(atr) - HORIZON_BARS
    if n < 200:
        return []
    scale = atr[:n]
    ratio = (spread[start:start + n] * point) / np.where(scale > 0, scale, np.nan)

    # Follow the entry bar's own direction. This is deliberately not a strategy:
    # every family in the book is some way of deciding that direction, so the
    # crudest possible version isolates the regime rather than the family.
    direction = np.sign(close[start:start + n] - open_[start:start + n])
    signed = (close[start + HORIZON_BARS:start + HORIZON_BARS + n]
              - close[start:start + n]) / scale * direction

    ok = ~np.isnan(ratio)
    ratio, signed = ratio[ok], signed[ok]
    if len(ratio) < 200:
        return []

    lo, hi = np.percentile(ratio, list(percentiles))
    masks = (("p0-p50", ratio <= lo),
             ("p50-p90", (ratio > lo) & (ratio <= hi)),
             ("p90+", ratio > hi))
    out = []
    for name, mask in masks:
        count = int(mask.sum())
        if count < 50:
            continue
        out.append(BandReading(
            name=name,
            trades=count,
            upper_ratio=float(ratio[mask].max()),
            continuation=float(np.mean(signed[mask] > 0)),
            net_atr=float(np.mean(signed[mask] - ratio[mask])),
        ))
    return out


def cap_from_bands(bands: list[BandReading], current: float) -> tuple[float, str]:
    """The widest band whose direction has not decayed sets the ceiling.

    Read as a slope, not a level. The absolute continuation rate sits within a
    couple of points of a coin flip on every symbol in the book - US30's best
    band is 47.9%, GER40's is 50.2% - so a fixed bar on the level would say
    almost nothing, and would say it mostly about which instrument it is. What
    separates them is the direction of travel across the buckets: US30 47.9 ->
    47.7 -> 45.0, GER40 49.0 -> 49.4 -> 50.2. Only the second shape earns room.

    Loosening needs a band beyond the cheapest to qualify; nothing else can widen
    a live gate. A symbol that qualifies nowhere past the first bucket keeps the
    cap it has - deliberately not a tightening, because the gate is not what is
    wrong with such a symbol and cutting it would only trade less of the same
    thing. So this can open a gate on evidence and can never close one without.
    """
    if not bands:
        return current, "olcum yok - mevcut cap korundu"
    # Both readings have to agree. Continuation alone was the first version and
    # it opened two gates it should not have: on the full series GER40's slope
    # is -0.22pp and NAS100's band was empty, while a windowed read (4 x 5000
    # bars) flipped GER40's sign in one window and US30's in three - and moving
    # the horizon from 8 bars to 16 reversed GER40 outright. A signal that
    # changes with the window is not a signal.
    #
    # net_atr - the follow-through actually left after paying the spread - is
    # the quantity the gate is supposed to protect, and it decays on both of
    # those symbols where continuation did not. Requiring the two to agree
    # costs nothing when the case is real and refuses every case measured so
    # far, which is the right answer for a book whose marginal bands priced
    # out at -0.035 R (FRA40) and -0.126 R (US30).
    base_cont, base_net = bands[0].continuation, bands[0].net_atr
    reached = None
    for band in bands[1:]:
        if band.continuation < base_cont or band.net_atr < base_net:
            break
        reached = band
    if reached is None:
        if len(bands) < 2:
            return current, "tek bant - cap degismedi"
        nxt = bands[1]
        which = ("yon" if nxt.continuation < base_cont else "net getiri")
        return current, (f"{which} en ucuz bandin otesinde zayifliyor "
                         f"(devam %{base_cont * 100:.1f} -> %{nxt.continuation * 100:.1f}, "
                         f"net {base_net:+.3f} -> {nxt.net_atr:+.3f}) - cap degismedi")
    cap = round(min(MAX_CAP, max(MIN_CAP, reached.upper_ratio)), 2)
    if cap <= current:
        # The asymmetry, enforced rather than merely intended: a band that
        # qualifies can still sit below the cap already in place, and returning
        # it would narrow a live gate on a reading that was only ever trusted to
        # widen one. GER40 is exactly that case - both readings hold through
        # p50-p90, whose ceiling is 0.09 against a live 0.11.
        return current, (f"{reached.name} tutuyor ama tavani mevcut cap'in altinda "
                         f"({cap:g} <= {current:g}) - daraltilmadi")
    return cap, (f"{reached.name} bandina kadar ikisi de tutuyor "
                 f"(devam %{base_cont * 100:.1f} -> %{reached.continuation * 100:.1f}, "
                 f"net {base_net:+.3f} -> {reached.net_atr:+.3f} ATR)")


def calibrate(symbol: str, timeframe: str, bars, point: float,
              current_cap: float) -> Calibration:
    bands = read_bands(bars, point)
    cap, reason = cap_from_bands(bands, current_cap)
    return Calibration(symbol=symbol, timeframe=timeframe, bands=bands,
                       cap=cap, reason=reason)
