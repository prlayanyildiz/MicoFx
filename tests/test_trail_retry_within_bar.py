"""A trail update the live quote blocked must be retried inside the same bar.

The trail level comes from the closed bar's close and does not move until the
next bar closes. Whether it can be *placed* depends on the live quote, because
the broker refuses a stop nearer than min_stop_distance to the current price.
Those pull apart whenever price retraces right after a bar closes.

The caller used to mark the ticket done for the bar the moment it called
_update_stop, so a "not placeable right now" became "not placeable for the rest
of the bar" - an hour on H1, on exactly the trades that ran far enough to earn
the update. _update_stop now reports whether the bar is settled, and only a
settled answer marks it.

Nothing here re-derives the trail *level* from the live quote, so a retry lands
the same stop the walk-forward validated; only feasibility is re-tested.
"""
from __future__ import annotations

import numpy as np
import pytest

from micofx.engine import Engine

TF_SEC = 300          # M5, matching _Cfg below
BAR_OPEN = 1_000_000  # the reference bar opens here, closing TF_SEC later


class _Bars:
    """Modelled on the real Bars, including the timestamp _update_stop reads.

    ``last_closed_time`` matters: the trail refuses a reference bar that closed
    before the position opened (see test_trail_ignores_pre_entry_bar), so these
    fixtures have to place their position inside the bar to exercise the rest.
    """

    def __init__(self, close: float) -> None:
        self.close = np.array([close - 1.0, close])
        self.high = self.close + 0.5
        self.low = self.close - 0.5

    @property
    def last_closed_time(self) -> int:
        return BAR_OPEN


class _Client:
    """Just enough broker for _update_stop: one quote, one min-stop, one modify."""

    def __init__(self, bid: float, min_stop: float = 1.0) -> None:
        self.bid = bid
        self._min_stop = min_stop
        self.modify_ok = True
        self.modifies: list[float] = []

    def tick(self, symbol):
        return {"bid": self.bid, "ask": self.bid + 0.01, "spread": 0.01}

    def min_stop_distance(self, symbol):
        return self._min_stop

    def modify_position(self, ticket, sl, tp, symbol):
        self.modifies.append(sl)
        return self.modify_ok


class _Cfg:
    symbol = "NAS100"
    magic = 7
    timeframe = "M5"          # TF_SEC above
    sl_atr_mult = 1.0
    trail_start_atr = 0.5
    trail_step_atr = 1.0
    trail_mode = "atr"
    trail_lookback = 5


def _engine(client) -> Engine:
    eng = Engine.__new__(Engine)          # no MT5 connect / no store
    eng.client = client
    eng.states = {}
    return eng


def _pos(sl: float, entry: float = 100.0, ticket: int = 1):
    # Opened inside the reference bar, so that bar closes after the fill and
    # its close is genuine post-entry price action.
    return {"ticket": ticket, "symbol": "NAS100", "side": "buy", "sl": sl,
            "tp": 0.0, "price_open": entry, "volume": 0.3, "magic": 7,
            "time": BAR_OPEN + 10}


ATR = 1.0


def test_live_quote_block_leaves_the_bar_unsettled():
    # Bar closed at 103 -> the trail wants 102. Price then snapped back to 101,
    # and min_stop 1.0 forbids any stop above 100.0 - behind the 100.5 the stop
    # already holds, so nothing can be placed at this instant.
    client = _Client(bid=101.0)
    eng = _engine(client)
    settled = eng._update_stop(_Cfg(), _pos(sl=100.5), ATR, _Bars(103.0))
    assert settled is False
    assert client.modifies == []


def test_a_clamped_but_still_improving_update_is_placed_and_settles():
    # The clamp is not itself a refusal: 102.5 - 1.0 = 101.5 is short of the
    # 102.0 wanted but still well ahead of the 100.5 held, so it goes in now
    # rather than waiting for a quote that may never come back.
    client = _Client(bid=102.5)
    eng = _engine(client)
    assert eng._update_stop(_Cfg(), _pos(sl=100.5), ATR, _Bars(103.0)) is True
    assert client.modifies == [pytest.approx(101.5)]


def test_a_stop_pinned_behind_breakeven_by_the_quote_stays_retryable():
    # Entry 100, stop already locked at breakeven. The live quote allows
    # nothing better than 99.5, which is worse than breakeven - skip and retry,
    # never hand back protection the trade already earned.
    client = _Client(bid=100.5)
    eng = _engine(client)
    assert eng._update_stop(_Cfg(), _pos(sl=100.0), ATR, _Bars(103.0)) is False
    assert client.modifies == []


def test_the_same_update_lands_once_the_quote_allows_it():
    # Same bar, same wanted level - price came back up, nothing re-derived.
    client = _Client(bid=104.0)
    eng = _engine(client)
    assert eng._update_stop(_Cfg(), _pos(sl=100.5), ATR, _Bars(103.0)) is True
    assert client.modifies == [pytest.approx(102.0)]


def test_a_rejected_modify_does_not_burn_the_bar():
    client = _Client(bid=104.0)
    client.modify_ok = False
    eng = _engine(client)
    assert eng._update_stop(_Cfg(), _pos(sl=100.5), ATR, _Bars(103.0)) is False


def test_a_bar_level_refusal_is_final_for_the_bar():
    # Price is below entry on the closed bar: no trail is owed, and no live
    # quote can change that before the next bar closes.
    client = _Client(bid=99.0)
    eng = _engine(client)
    assert eng._update_stop(_Cfg(), _pos(sl=98.0), ATR, _Bars(99.0)) is True
    assert client.modifies == []


def test_trail_not_yet_armed_is_also_final_for_the_bar():
    # +0.2 ATR of profit, trail arms at 0.5 - a bar-level fact.
    client = _Client(bid=100.2)
    eng = _engine(client)
    assert eng._update_stop(_Cfg(), _pos(sl=99.0), ATR, _Bars(100.2)) is True
    assert client.modifies == []


def test_too_small_an_improvement_is_final_when_the_quote_did_not_bind():
    # Wanted 102.0, already at 101.9: a real but sub-step improvement, and the
    # live quote (104) never clamped it - so there is nothing to retry for.
    client = _Client(bid=104.0)
    eng = _engine(client)
    assert eng._update_stop(_Cfg(), _pos(sl=101.9), ATR, _Bars(103.0)) is True
    assert client.modifies == []


def test_without_bars_every_refusal_stays_retryable():
    # No bar series: the reference IS the live quote, so nothing decided here
    # is fixed for the bar.
    client = _Client(bid=99.0)
    eng = _engine(client)
    assert eng._update_stop(_Cfg(), _pos(sl=98.0), ATR, None) is False


def test_the_stop_still_never_moves_backwards():
    # The retry path must not become a way to walk a stop back. Wanted 102.0,
    # current SL is already 103.5 (trailed on an earlier, higher bar).
    client = _Client(bid=104.0)
    eng = _engine(client)
    eng._update_stop(_Cfg(), _pos(sl=103.5), ATR, _Bars(103.0))
    assert client.modifies == []
