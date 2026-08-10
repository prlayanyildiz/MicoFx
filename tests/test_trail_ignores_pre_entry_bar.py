"""The trail must not measure profit against a bar that closed before the fill.

An entry fires on a signal from the bar that has just closed, so on the very
first management pass that same bar is still the last closed one. Its close is
where price was BEFORE the fill - not profit the trade has made. Any entry that
fills better than its signal bar's close (most of a mean-reversion book: buying
the dip under it is the entire idea) therefore read as instantly in profit and
had its stop ratcheted in on the strength of it, seconds after opening.

Observed live on 2026-08-10:

    14:22:06 BUY 0.05 SpotBrent @ 85.36600 SL=84.81900
    14:22:08 SL guncellendi -> 85.12840 (kar 0.50xATR)

Two seconds. The reference was 85.7535, the signal bar's close, 0.39 above the
fill. The position was sized against 0.547 of risk and its stop was now 0.238
away - 43% of the distance it was sized for - so it was left to die on noise
the walk-forward gave it room to survive.

The replay never did this: it enters at bar j0's open and first consults
close[j0], a bar that closes after the entry by construction. This restores
that ordering live.
"""
from __future__ import annotations

import numpy as np
import pytest

from micofx.engine import Engine

TF_SEC = 900          # M15
BAR_OPEN = 1_000_000  # the last closed bar opens here...
BAR_CLOSE = BAR_OPEN + TF_SEC   # ...and closes here


class _Bars:
    """One closed bar, opening at BAR_OPEN, closing at BAR_CLOSE."""

    def __init__(self, close: float) -> None:
        self.close = np.array([close - 1.0, close])
        self.high = self.close + 0.5
        self.low = self.close - 0.5

    @property
    def last_closed_time(self) -> int:
        return BAR_OPEN


class _Client:
    def __init__(self, bid: float, min_stop: float = 0.01) -> None:
        self.bid = bid
        self._min_stop = min_stop
        self.modifies: list[float] = []

    def tick(self, symbol):
        return {"bid": self.bid, "ask": self.bid + 0.01, "spread": 0.01}

    def min_stop_distance(self, symbol):
        return self._min_stop

    def modify_position(self, ticket, sl, tp, symbol):
        self.modifies.append(sl)
        return True


class _Cfg:
    symbol = "SpotBrent"
    magic = 7
    timeframe = "M15"
    sl_atr_mult = 0.7
    trail_start_atr = 0.3
    trail_step_atr = 0.8
    trail_mode = "atr"
    trail_lookback = 5


def _engine(client) -> Engine:
    eng = Engine.__new__(Engine)
    eng.client = client
    eng.states = {}
    return eng


# The live numbers from the log above.
ATR = 0.7814
ENTRY = 85.366
SIGNAL_BAR_CLOSE = 85.7535      # closed BEFORE the fill, 0.39 above it


def _pos(opened_at: int, sl: float = 84.819):
    return {"ticket": 1, "symbol": "SpotBrent", "side": "buy", "sl": sl,
            "tp": 0.0, "price_open": ENTRY, "volume": 0.05, "magic": 7,
            "time": opened_at}


def test_a_bar_that_closed_before_the_fill_moves_nothing():
    # Entry landed after the reference bar closed - the exact live case.
    client = _Client(bid=SIGNAL_BAR_CLOSE)
    eng = _engine(client)
    settled = eng._update_stop(_Cfg(), _pos(opened_at=BAR_CLOSE + 6), ATR,
                               _Bars(SIGNAL_BAR_CLOSE))
    assert client.modifies == []
    # Nothing can change until a new bar closes, so the bar is done.
    assert settled is True


def test_the_same_bar_is_honoured_once_it_closes_after_the_entry():
    # A position opened during that bar: it closes after the fill, so its close
    # is real post-entry price action and the trail is owed.
    client = _Client(bid=SIGNAL_BAR_CLOSE)
    eng = _engine(client)
    settled = eng._update_stop(_Cfg(), _pos(opened_at=BAR_OPEN + 10), ATR,
                               _Bars(SIGNAL_BAR_CLOSE))
    assert settled is True
    assert client.modifies == [pytest.approx(SIGNAL_BAR_CLOSE - ATR * 0.8)]


def test_the_position_keeps_the_risk_distance_it_was_sized_for():
    # The whole point: on the first pass the stop stays where the entry put it.
    client = _Client(bid=SIGNAL_BAR_CLOSE)
    eng = _engine(client)
    pos = _pos(opened_at=BAR_CLOSE + 6)
    eng._update_stop(_Cfg(), pos, ATR, _Bars(SIGNAL_BAR_CLOSE))
    assert pos["sl"] == 84.819
    assert ENTRY - pos["sl"] == pytest.approx(ATR * _Cfg.sl_atr_mult, abs=1e-3)


def test_a_fill_exactly_on_the_bar_close_is_still_excluded():
    # Equal timestamps mean the bar did not close after the entry.
    client = _Client(bid=SIGNAL_BAR_CLOSE)
    eng = _engine(client)
    eng._update_stop(_Cfg(), _pos(opened_at=BAR_CLOSE), ATR,
                     _Bars(SIGNAL_BAR_CLOSE))
    assert client.modifies == []


def test_a_position_with_no_open_time_is_not_blocked():
    # Defensive: a caller that cannot supply the time must not silently lose
    # its trail forever.
    client = _Client(bid=SIGNAL_BAR_CLOSE)
    eng = _engine(client)
    pos = _pos(opened_at=0)
    pos.pop("time")
    eng._update_stop(_Cfg(), pos, ATR, _Bars(SIGNAL_BAR_CLOSE))
    assert client.modifies == [pytest.approx(SIGNAL_BAR_CLOSE - ATR * 0.8)]


def test_the_quote_only_path_is_unaffected():
    # No bars: the reference is the live quote, which is current by definition,
    # so the entry-time gate has nothing to exclude and the trail lands.
    client = _Client(bid=SIGNAL_BAR_CLOSE)
    eng = _engine(client)
    settled = eng._update_stop(_Cfg(), _pos(opened_at=BAR_CLOSE + 6), ATR, None)
    assert settled is True          # the modify itself succeeded
    assert client.modifies == [pytest.approx(SIGNAL_BAR_CLOSE - ATR * 0.8)]
