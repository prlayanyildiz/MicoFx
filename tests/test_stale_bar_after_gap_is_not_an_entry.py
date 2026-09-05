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
    eng._entry_blocks = {}
    eng._entry_last_bar = {}
    eng._entry_events = []
    eng._entry_blocks_since = 0.0
    eng._entry_blocks_dirty = False
    eng._entry_events_dirty = False
    return eng


def _cfg():
    return SymbolConfig(symbol="GER40", group="index", magic=1, timeframe="M30")


def _open_session():
    return SimpleNamespace(open=True, reason="", minutes_to_close=None,
                           minutes_to_open=None, window="03:15-22:59")


def _closed_session():
    return SimpleNamespace(open=False, reason="", minutes_to_close=None,
                           minutes_to_open=61, window="01:00-23:59")


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


def test_a_stale_gap_bar_is_counted_as_bar_bosluk(monkeypatch):
    """01:00 US30: the refuse was right, the counter never saw it.

    _evaluate returns False at bar_bosluk before _try_entry, so the
    ready-loop tally never ran. The first session bar every night is this
    path; it must show up as a signal, not vanish.
    """
    from micofx import sessions as sessions_mod

    eng = _make_engine()
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: _open_session())
    monkeypatch.setattr(sessions_mod, "should_flatten", lambda *a, **kw: False)

    def _fake_refresh(cfg_arg, state_arg, params):
        state_arg.last_bar = FRIDAY_BAR
        state_arg.primary_signal = "buy"
        state_arg.atr = 30.1
        return True

    eng._refresh_signals = _fake_refresh
    state = SymbolState("GER40")
    eng._evaluate(
        _cfg(), state, server_now=float(MONDAY_OPEN),
        account={"equity": 1000.0}, allow_entry=True,
    )
    data = eng.entry_blocks()
    assert data["totals"].get("bar_bosluk") == 1, data
    assert data["signals"] == 1


def test_an_already_filled_bar_is_counted_as_bar_doldu(monkeypatch):
    """Restart ghost of the same bar: refuse is right, counter never saw it.

    Same-bar lock is _evaluate False before _try_entry. 01:04 US30 after
    the 01:00 restart was this path; entry_block_events only later showed
    the 01:10 spread.
    """
    from micofx import sessions as sessions_mod

    eng = _make_engine()
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: _open_session())
    monkeypatch.setattr(sessions_mod, "should_flatten", lambda *a, **kw: False)

    tf_sec = timeframe_seconds("M30")
    now = float(MONDAY_OPEN + 30 * 60)
    last_bar = int(now - tf_sec)

    def _fake_refresh(cfg_arg, state_arg, params):
        state_arg.last_bar = last_bar
        state_arg.primary_signal = "buy"
        state_arg.atr = 30.1
        return True

    eng._refresh_signals = _fake_refresh
    eng._filled_bars = {"GER40": {"primary": last_bar}}
    state = SymbolState("GER40")
    wants = eng._evaluate(
        _cfg(), state, server_now=now,
        account={"equity": 1000.0}, allow_entry=True,
    )
    assert wants is False
    assert state.entry_block == "bar_doldu"
    data = eng.entry_blocks()
    assert data["totals"].get("bar_doldu") == 1, data
    assert data["signals"] == 1


def test_a_signalled_closed_session_is_counted_as_seans_disi(monkeypatch):
    """_merge_signals runs before the session gate, so a live signal can
    be refused here. Same invisibility as bar_bosluk, one gate earlier.
    US30 is closed 00:00-01:00 every night; those refusals must show up.
    """
    from micofx import sessions as sessions_mod

    eng = _make_engine()
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: _closed_session())
    monkeypatch.setattr(sessions_mod, "should_flatten", lambda *a, **kw: False)

    tf_sec = timeframe_seconds("M30")
    now = float(MONDAY_OPEN - 30 * 60)
    last_bar = int(now - tf_sec)

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
    assert wants is False
    assert state.entry_block == "seans_disi"
    data = eng.entry_blocks()
    assert data["totals"].get("seans_disi") == 1, data
    assert data["signals"] == 1


def test_a_signalled_hour_block_is_counted_as_saat_kapali(monkeypatch):
    """blocked_entry_hours closes sess.open but must not look like seans_disi."""
    from micofx import sessions as sessions_mod
    from micofx.sessions import SessionState

    eng = _make_engine()
    monkeypatch.setattr(
        sessions_mod, "evaluate",
        lambda *a, **kw: SessionState(
            open=False, reason="saat kapali",
            minutes_to_close=None, minutes_to_open=56, window="7/24",
        ),
    )
    monkeypatch.setattr(sessions_mod, "should_flatten", lambda *a, **kw: False)

    tf_sec = timeframe_seconds("M30")
    now = float(MONDAY_OPEN + 30 * 60)
    last_bar = int(now - tf_sec)

    def _fake_refresh(cfg_arg, state_arg, params):
        state_arg.last_bar = last_bar
        state_arg.primary_signal = "buy"
        state_arg.atr = 30.1
        return True

    eng._refresh_signals = _fake_refresh
    state = SymbolState("JPN225")
    wants = eng._evaluate(
        _cfg(), state, server_now=now,
        account={"equity": 1000.0}, allow_entry=True,
    )
    assert wants is False
    assert state.entry_block == "saat_kapali"
    assert "saat kapali" in state.note
    assert "seans disi" not in state.note
    data = eng.entry_blocks()
    assert data["totals"].get("saat_kapali") == 1, data
    assert data["totals"].get("seans_disi") in (None, 0)


def test_a_closed_session_without_a_signal_stays_silent(monkeypatch):
    """The drown case: closed-session polls with nothing to refuse."""
    from micofx import sessions as sessions_mod

    eng = _make_engine()
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: _closed_session())
    monkeypatch.setattr(sessions_mod, "should_flatten", lambda *a, **kw: False)

    def _fake_refresh(cfg_arg, state_arg, params):
        state_arg.last_bar = FRIDAY_BAR
        state_arg.primary_signal = ""
        state_arg.atr = 30.1
        return True

    eng._refresh_signals = _fake_refresh
    state = SymbolState("GER40")
    eng._evaluate(
        _cfg(), state, server_now=float(MONDAY_OPEN - 30 * 60),
        account={"equity": 1000.0}, allow_entry=True,
    )
    data = eng.entry_blocks()
    assert data["signals"] == 0, data
    assert data["totals"] == {}


def test_a_signalled_closed_market_is_counted_as_piyasa_kapali(monkeypatch):
    """trade_all_hours makes sess.open true; this gate is the real halt."""
    from micofx import sessions as sessions_mod

    eng = _make_engine()
    eng.client = SimpleNamespace(
        connected=True,
        resolve=lambda symbol: symbol,
        tick=lambda symbol: None,
        market_open=lambda symbol: False,
    )
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: _open_session())
    monkeypatch.setattr(sessions_mod, "should_flatten", lambda *a, **kw: False)

    tf_sec = timeframe_seconds("M30")
    now = float(MONDAY_OPEN + 30 * 60)
    last_bar = int(now - tf_sec)

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
    assert wants is False
    assert state.entry_block == "piyasa_kapali"
    data = eng.entry_blocks()
    assert data["totals"].get("piyasa_kapali") == 1, data
    assert data["signals"] == 1

