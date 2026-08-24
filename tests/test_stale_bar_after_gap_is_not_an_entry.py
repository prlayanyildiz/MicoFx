"""A Friday close must not enter on Monday session open after a restart.

_evaluate already clears the signal chain when the session is shut, so a
process that stays up across the weekend starts the new session from
nothing. A restart does not: SymbolState is rebuilt empty, last_bar is 0,
and _refresh_signals treats the still-last-closed Friday stamp as a new
bar. Session-close clearing never ran in this process - there was nothing
in memory to clear.

Measured 24.08: GER40 BUY 363660277, Friday 22:30 UTC bar, Monday 03:15 UTC
fill (GER40 session open), stopped out for -1R in 12 minutes. _filled_bars
does not cover this - that lock is same-bar-after-restart, and this bar had
never filled. gec_dolum is a late-fill duplicate guard, not a max signal
age. saat_bayat is a dead broker clock, and the clock was fine.
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

from micofx.engine import _MAX_SIGNAL_BAR_AGE_BARS, Engine, SymbolState
from micofx.models import SymbolConfig
from micofx.mt5client import timeframe_seconds

# Friday 21.08.2026 22:30 UTC - GER40's last closed M30 before the weekend.
FRIDAY_BAR = 1_787_351_400
# Monday 24.08.2026 03:15 UTC - GER40 session open, 52.75 hours later.
MONDAY_OPEN = 1_787_541_300


class _FakeStore:
    def __init__(self):
        self.settings: dict = {}
        self.system = SimpleNamespace(trade_all_hours=True, day_end_flatten_min=0)


def _make_engine():
    eng = object.__new__(Engine)
    eng.store = _FakeStore()
    eng.client = SimpleNamespace(
        connected=True,
        resolve=lambda symbol: symbol,
        tick=lambda symbol: None,
        market_open=lambda symbol: True,
    )
    eng.entry_lock = threading.Lock()
    eng._positions = []
    eng._filled_bars = {}
    eng._spread_ratio = {}
    eng._spread_ratio_dirty = False
    eng.states = {}
    return eng


def _cfg():
    return SymbolConfig(symbol="GER40", group="index", magic=1, timeframe="M30")


def _open_session():
    return SimpleNamespace(open=True, reason="", minutes_to_close=None,
                           minutes_to_open=None, window="03:15-22:59")


def test_friday_bar_does_not_enter_on_monday_session_open(monkeypatch):
    """Restart into the gap: last_bar was 0, Friday's stamp looks fresh."""
    from micofx import sessions as sessions_mod

    eng = _make_engine()
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: _open_session())
    monkeypatch.setattr(sessions_mod, "should_flatten", lambda *a, **kw: False)

    friday = FRIDAY_BAR

    def _fake_refresh(cfg_arg, state_arg, params):
        # Empty SymbolState after restart: last_bar 0 -> Friday looks new.
        state_arg.last_bar = friday
        state_arg.primary_signal = "buy"
        state_arg.atr = 30.1
        return True

    eng._refresh_signals = _fake_refresh
    state = SymbolState("GER40")

    wants = eng._evaluate(
        _cfg(), state, server_now=float(MONDAY_OPEN),
        account={"equity": 1000.0}, allow_entry=True,
    )

    assert wants is False
    assert state.entry_block == "bar_bosluk"
    assert state.signal == ""
    assert state.primary_signal == ""
    assert state.pending_bar_key == (0, 0)
    assert "bosluk" in state.note


def test_a_bar_inside_two_timeframes_is_still_an_entry(monkeypatch):
    """The gate must not kill the live path: enter during the next bar."""
    from micofx import sessions as sessions_mod

    eng = _make_engine()
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: _open_session())
    monkeypatch.setattr(sessions_mod, "should_flatten", lambda *a, **kw: False)

    tf_sec = timeframe_seconds("M30")
    now = float(MONDAY_OPEN + 30 * 60)  # 03:45, well inside the session
    last_bar = int(now - tf_sec)        # the M30 that just closed

    def _fake_refresh(cfg_arg, state_arg, params):
        state_arg.last_bar = last_bar
        state_arg.primary_signal = "sell"
        state_arg.atr = 30.1
        return True

    eng._refresh_signals = _fake_refresh
    state = SymbolState("GER40")

    wants = eng._evaluate(
        _cfg(), state, server_now=now,
        account={"equity": 1000.0}, allow_entry=True,
    )

    assert wants is True
    assert state.signal == "sell"
    assert state.pending_bar_key == ("primary", last_bar)
    assert state.entry_block != "bar_bosluk"


def test_exactly_two_timeframes_of_age_is_still_offered(monkeypatch):
    """Boundary is strict greater-than, so one extra bar of poll slack holds."""
    from micofx import sessions as sessions_mod

    eng = _make_engine()
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: _open_session())
    monkeypatch.setattr(sessions_mod, "should_flatten", lambda *a, **kw: False)

    tf_sec = timeframe_seconds("M30")
    now = float(MONDAY_OPEN + 60 * 60)
    last_bar = int(now - _MAX_SIGNAL_BAR_AGE_BARS * tf_sec)

    def _fake_refresh(cfg_arg, state_arg, params):
        state_arg.last_bar = last_bar
        state_arg.primary_signal = "buy"
        state_arg.atr = 30.1
        return True

    eng._refresh_signals = _fake_refresh
    state = SymbolState("GER40")

    wants = eng._evaluate(
        _cfg(), state, server_now=now,
        account={"equity": 1000.0}, allow_entry=True,
    )

    assert wants is True
    assert (now - last_bar) == _MAX_SIGNAL_BAR_AGE_BARS * tf_sec
