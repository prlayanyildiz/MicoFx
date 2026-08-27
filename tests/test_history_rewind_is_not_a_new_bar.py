"""A copy_rates stub that ends on an older bar is not a new signal.

_refresh_signals treats last_closed != last_bar as a fresh bar. After an
attach, MT5 often returns a short history whose last closed stamp is
*earlier* than the one this process already scored. The equality check
does not catch that: the stamps differ, so the older bar is computed and
emitted as if it had just closed.

Measured 24.08 01:00: NAS100 SIGNAL identical to 22.08 08:26
(K=40.1 D=52.1 ATR=56.39410). IPC dropped at 17:18; the process was still
the Saturday one (restart was 01:17), so last_bar was not 0. Friday
afternoon M30 bars would have advanced last_bar past 08:26. The only way
that exact snapshot fires again is last_closed moving backwards.

The 01:30 NAS100 signal is a different bar (K=18.8 D=31.8) and a real
session fill. This gate is only the rewind.
"""
from __future__ import annotations

import numpy as np

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig
from micofx.strategy import Params, required_bars

TF = 1800
FRIDAY_MORNING = 1_787_308_000   # 22.08 08:26-shaped
FRIDAY_AFTERNOON = 1_787_338_000  # later the same day


class _Bars:
    def __init__(self, n, last_closed):
        self.n = n
        t = np.arange(n, dtype=np.int64) * TF
        t[-1] = int(last_closed)
        c = 100 + np.arange(n) * 0.01
        self.time, self.close = t, c
        self.high, self.low = c + 0.5, c - 0.5
        self.open = c
        self.spread = np.zeros(n)
        self.volume = np.ones(n)
        self.last_closed_time = int(last_closed)

    def __len__(self):
        return self.n


def _engine(last_closed, broker_now=0.0):
    # The family _cfg() actually configures, not the dataclass default - the
    # engine sizes this window from the symbol's own params, and the default
    # moved on 27.08 when t3_stoch retired.
    need = required_bars(Params(strategy="mtf_pullback"))
    n = max(60, need // 2)
    now = float(broker_now)

    class _Client:
        connected = True

        def bars(self, symbol, timeframe, count):
            return _Bars(n, last_closed)

        def broker_now(self):
            return now

        def info(self, symbol):
            return {"point": 0.01, "tick_value": 1.0, "tick_size": 0.01}

    eng = Engine.__new__(Engine)
    eng.client = _Client()
    return eng, n


def _cfg():
    return SymbolConfig(symbol="NAS100", group="index", magic=1,
                        timeframe="M30", strategy="mtf_pullback")


def test_an_older_last_closed_does_not_replace_the_scored_bar():
    eng, _n = _engine(FRIDAY_MORNING)
    state = SymbolState("NAS100")
    state.last_bar = FRIDAY_AFTERNOON
    state.last_fetch = 0.0
    state.primary_signal = ""
    before = state.last_bar

    fresh = eng._refresh_signals(_cfg(), state, Params.from_config(_cfg()))

    assert fresh is False
    assert state.last_bar == before
    assert state.primary_signal == ""


def test_a_newer_last_closed_is_still_a_new_bar():
    """The gate must not freeze last_bar when history actually advances."""
    later = FRIDAY_AFTERNOON + TF
    eng, _n = _engine(later)
    state = SymbolState("NAS100")
    state.last_bar = FRIDAY_AFTERNOON
    state.last_fetch = 0.0

    fresh = eng._refresh_signals(_cfg(), state, Params.from_config(_cfg()))

    assert fresh is True
    assert state.last_bar == later


def test_a_future_last_closed_does_not_raise_the_yardstick():
    """Tick path already drops future stamps; bars must too or rewind locks."""
    broker = float(FRIDAY_AFTERNOON)
    future = FRIDAY_AFTERNOON + 86400 * 30
    eng, _n = _engine(future, broker_now=broker)
    state = SymbolState("NAS100")
    state.last_bar = FRIDAY_AFTERNOON
    state.last_fetch = 0.0

    fresh = eng._refresh_signals(_cfg(), state, Params.from_config(_cfg()))

    assert fresh is False
    assert state.last_bar == FRIDAY_AFTERNOON
    assert "ileri" in state.note


def test_a_poisoned_future_last_bar_does_not_silence_the_symbol():
    """Escape: last_bar ahead of the broker clock is not a scored bar."""
    broker = float(FRIDAY_AFTERNOON + TF)
    closed = FRIDAY_AFTERNOON + TF
    eng, _n = _engine(closed, broker_now=broker)
    state = SymbolState("NAS100")
    state.last_bar = FRIDAY_AFTERNOON + 86400 * 30
    state.last_fetch = 0.0

    fresh = eng._refresh_signals(_cfg(), state, Params.from_config(_cfg()))

    assert fresh is True
    assert state.last_bar == closed


def test_bar_stamp_latch_prunes_dead_symbols_and_caps():
    eng = Engine.__new__(Engine)
    eng.store = type("S", (), {"symbols": {"NAS100": object()}})()
    for i in range(70):
        eng._note_bar_stamp("NAS100", "rewind", i, "x")
    assert len(eng._bar_rewind_logged) <= 64
    eng._note_bar_stamp("DEAD", "rewind", 1, "x")
    # DEAD is not in store.symbols; the next live call drops it.
    eng._note_bar_stamp("NAS100", "rewind", 99, "x")
    assert all(k[1] == "NAS100" for k in eng._bar_rewind_logged)
