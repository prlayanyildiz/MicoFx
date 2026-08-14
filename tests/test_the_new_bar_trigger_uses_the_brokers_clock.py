"""A bar's timestamp may only be compared against the broker's own clock.

``state.next_bar_at`` is built from ``bars.last_closed_time`` - a naive epoch
holding the broker's wall-clock reading. ``server_now()`` is a true epoch, this
machine's. Subtracting one from the other leaves the broker's entire UTC offset
in the answer: +10800 on this GMT+3 server.

Measured 15.08 at 00:01 local: the last closed M5 bar was stamped 164 minutes
"ahead" of local time and ``next_bar_at`` 174 minutes ahead, so
``server_now() >= next_bar_at`` was False on every cycle and had been for the
life of the process. Nothing looked broken, because ``stale`` fires every 45
seconds and refreshed the bars anyway - the intended trigger was dead and a
fallback carried the system silently. It also moved every entry off the bar
close and onto that 45-second timer, which is what the measured 21-30 seconds
into the bar entry timing was.

``market_open`` had the identical bug and its docstring already states the rule:
compare two readings of the same clock, which cancels the offset and needs no
detection. This is that rule applied to the second place that broke it.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.mt5client import MT5Client

SRC = inspect.getsource(Engine._refresh_signals)


def test_the_due_check_reads_the_broker_clock():
    assert "self.client.broker_now()" in SRC, (
        "next_bar_at is broker-stamped; the clock it is compared against must be too")


def test_the_due_check_no_longer_reads_the_local_clock():
    due = SRC[SRC.index("due ="):SRC.index("stale =")]
    assert "server_now()" not in due, (
        "server_now() is a true epoch and leaves the broker's UTC offset in the answer")


def test_an_unread_broker_clock_falls_back_rather_than_firing():
    """0.0 means 'no tick yet', not 'the epoch began'.

    Without the guard, a zero clock makes `0 >= next_bar_at` false anyway, but
    only by accident of sign - and a future refactor that flips the comparison
    would then treat an unknown clock as an infinitely old one and refetch bars
    every cycle for every symbol.
    """
    assert "broker_now > 0.0 and" in SRC


def test_the_client_exposes_the_broker_clock():
    assert hasattr(MT5Client, "broker_now")
    doc = inspect.getdoc(MT5Client.broker_now) or ""
    assert "0.0" in doc, "callers have to be told what an unread clock looks like"


def test_the_broker_clock_starts_unknown_and_tracks_the_newest_reading():
    client = MT5Client.__new__(MT5Client)
    client._broker_now = 0.0
    assert client.broker_now() == 0.0

    client._broker_now = 1786751699.0
    assert client.broker_now() == 1786751699.0


def test_market_open_still_uses_the_same_yardstick():
    """The rule this fix follows is stated there; it must not drift apart."""
    src = inspect.getsource(MT5Client.market_open)
    assert "self._broker_now" in src


def test_the_execution_deal_window_uses_the_broker_clock_too():
    """The second place a true epoch was handed to a broker-stamped query.

    ``_measure_broker_exits`` asked deals_since() for the last two hours off
    time.time(); measured 15.08, that returned a 3.2-hour span. Wider is not
    free - reap() matches a closed position against these deals, so the extra
    hours are candidates it has to discriminate between.

    ``_day_start_epoch`` was checked at the same time and is correct: it builds
    the boundary with calendar.timegm() from the local calendar date, which
    produces the same naive encoding the broker stamps, so the two line up.
    """
    src = inspect.getsource(Engine)
    calls = [line.strip() for line in src.splitlines() if "deals_since(" in line
             and not line.strip().startswith("#")]
    assert calls, "no deals_since call found - has it been renamed?"
    bad = [c for c in calls if "time.time()" in c]
    assert not bad, ("deals_since takes a broker-stamped bound, not a true epoch: "
                     + "; ".join(bad))
    assert any("since" in c or "broker_now" in c for c in calls)


def test_the_day_boundary_still_uses_the_naive_encoding():
    """Correct already - pinned so a 'tidy-up' does not turn it into mktime."""
    src = inspect.getsource(Engine._day_start_epoch)
    assert "calendar.timegm" in src
    assert "mktime" not in src, (
        "mktime returns a true epoch and would shift the trading day by the "
        "broker's whole UTC offset")


# --------------------------------------------------------------- behaviour
# The source assertions above are necessary but not sufficient: Cursor put the
# local clock back while leaving broker_now() in place and
# test_the_due_check_reads_the_broker_clock stayed green. These drive the real
# decision instead.

class _Bars:
    def __init__(self, last_closed: int, n: int = 900):
        import numpy as np
        self.last_closed_time = last_closed
        self.time = np.arange(last_closed - (n - 1) * 300, last_closed + 300, 300)
        self.open = np.full(n, 100.0)
        self.high = np.full(n, 100.5)
        self.low = np.full(n, 99.5)
        self.close = np.full(n, 100.0)
        self.spread = np.full(n, 10.0)
        self.volume = np.full(n, 1.0)

    def __len__(self):
        return len(self.close)


class _Client:
    """Broker clock three hours ahead of the machine's, as measured live."""

    OFFSET = 10800

    def __init__(self, last_closed: int):
        self._last_closed = last_closed
        self.bar_calls = 0

    def broker_now(self):
        import time
        return time.time() + self.OFFSET

    def server_now(self):
        import time
        return time.time()

    def bars(self, symbol, timeframe, count):
        self.bar_calls += 1
        return _Bars(self._last_closed)

    def info(self, symbol):
        # Enough for the cost series _refresh_signals builds after the fetch.
        return {"point": 0.01, "tick_value": 1.0, "tick_size": 0.01}


def _engine(client) -> Engine:
    eng = Engine.__new__(Engine)
    eng.client = client
    return eng


def _state(next_bar_at: float, last_bar: int):
    from micofx.engine import SymbolState
    st = SymbolState("XAUUSD")
    st.next_bar_at = next_bar_at
    st.last_bar = last_bar
    import time
    st.last_fetch = time.time()          # not stale: only `due` can fire
    return st


def _params():
    from micofx.models import SymbolConfig
    from micofx.strategy import Params
    return Params.from_config(SymbolConfig(symbol="XAUUSD", strategy="t3_stoch",
                                           timeframe="M5"))


def test_a_closed_bar_on_the_brokers_clock_triggers_a_refetch():
    """The whole defect: next_bar_at is broker-stamped and had passed, but the
    machine's clock is three hours behind it, so the old comparison said no."""
    import time

    from micofx.models import SymbolConfig

    broker_last_closed = int(time.time() + _Client.OFFSET) - 60
    client = _Client(broker_last_closed)
    eng = _engine(client)
    # next_bar_at already reached on the broker's clock, nowhere near it on ours.
    state = _state(next_bar_at=time.time() + _Client.OFFSET - 30,
                   last_bar=broker_last_closed - 300)

    eng._refresh_signals(SymbolConfig(symbol="XAUUSD", strategy="t3_stoch",
                                      timeframe="M5"), state, _params())

    assert client.bar_calls == 1, (
        "the bar closed on the clock that stamps it and nothing was fetched")


def test_a_bar_that_has_not_closed_yet_does_not_refetch():
    """The counterpart: `due` must still be able to say no."""
    import time

    from micofx.models import SymbolConfig

    broker_last_closed = int(time.time() + _Client.OFFSET) - 60
    client = _Client(broker_last_closed)
    eng = _engine(client)
    state = _state(next_bar_at=time.time() + _Client.OFFSET + 600,
                   last_bar=broker_last_closed)

    eng._refresh_signals(SymbolConfig(symbol="XAUUSD", strategy="t3_stoch",
                                      timeframe="M5"), state, _params())

    assert client.bar_calls == 0, "refetched a bar that has not closed"
