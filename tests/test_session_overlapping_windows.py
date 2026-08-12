"""Overlapping session windows must not wind the trade down at the earlier close.

``evaluate`` walks every configured window, keeps the ones containing this
minute, and reports ``minutes_to_close`` as the SMALLEST remaining among them.
With one window - which is every symbol in the live book right now - smallest
and largest are the same number and nothing shows. With two that overlap they
are not, and the smaller one is the wrong answer: the session is open until the
LAST containing window ends, because while the earlier one expires the later one
still holds the minute.

``should_flatten`` reads exactly that number:

    return state.minutes_to_close <= cfg.flat_before_close_min

so on a symbol windowed 08:00-12:00 and 09:00-17:00, at 11:55 it reports five
minutes left and the engine force-closes every open position - five hours before
the session actually ends. Six minutes later the first window has expired, only
the second still matches, ``minutes_to_close`` jumps back to five hours and
entries resume. A flatten followed by re-entry, from a config that never asked
for either.

Not reachable in the live book: all nineteen enabled symbols carry exactly one
window. Reachable by configuration - ``_validate_sessions`` checks the format
and refuses a zero-length window, but says nothing about overlap, and
``session_windows()`` returns the list unmerged.

The label had the same split: ``active`` was overwritten by whichever window
matched last while ``best_close`` came from whichever expired first, so the
panel could name one window and count down another.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import sessions
from micofx.models import SymbolConfig


def _at(hh: int, mm: int) -> float:
    """Local epoch for 2026-08-12 (a Wednesday) at hh:mm."""
    return time.mktime((2026, 8, 12, hh, mm, 0, 0, 0, -1))


def _cfg(windows: list[tuple[str, str]], flat: int = 5) -> SymbolConfig:
    cfg = SymbolConfig(symbol="TEST", magic=1)
    cfg.use_sessions = True
    cfg.trade_days = [1, 2, 3, 4, 5]
    cfg.flat_before_close_min = flat
    cfg.sessions = [{"start": s, "end": e} for s, e in windows]
    return cfg


OVERLAP = [("08:00", "12:00"), ("09:00", "17:00")]


# ------------------------------------------------------- the defect

def test_the_later_window_keeps_the_session_open():
    state = sessions.evaluate(_cfg(OVERLAP), _at(11, 55))
    assert state.open is True
    assert state.minutes_to_close == 305, (
        f"erken kapanan pencereye gore geri sayiyor: {state.minutes_to_close}")


def test_no_flatten_five_hours_before_the_session_ends():
    assert not sessions.should_flatten(_cfg(OVERLAP), _at(11, 55)), (
        "pozisyonlar seans bitiminden bes saat once zorla kapatiliyor")


def test_the_state_does_not_flip_across_the_earlier_close():
    """11:55 and 12:01 are both inside 09:00-17:00; nothing should change
    character between them."""
    cfg = _cfg(OVERLAP)
    before = sessions.evaluate(cfg, _at(11, 55))
    after = sessions.evaluate(cfg, _at(12, 1))
    assert before.open is after.open is True
    assert before.minutes_to_close > after.minutes_to_close, "geri sayim ilerlemeli"
    assert sessions.should_flatten(cfg, _at(11, 55)) is sessions.should_flatten(
        cfg, _at(12, 1)) is False


def test_the_named_window_is_the_one_being_counted_down():
    state = sessions.evaluate(_cfg(OVERLAP), _at(11, 55))
    assert state.window == "09:00-17:00", (
        f"panel {state.window} yaziyor ama baska pencereye gore sayiyor")


# --------------------------------------------- the wind-down still has to work

def test_the_flatten_fires_before_the_real_close():
    cfg = _cfg(OVERLAP)
    assert sessions.should_flatten(cfg, _at(16, 56)) is True
    assert sessions.evaluate(cfg, _at(16, 56)).minutes_to_close == 4


def test_a_single_window_is_unchanged():
    cfg = _cfg([("09:00", "17:00")])
    assert sessions.evaluate(cfg, _at(11, 55)).minutes_to_close == 305
    assert sessions.should_flatten(cfg, _at(16, 56)) is True
    assert sessions.should_flatten(cfg, _at(11, 55)) is False


def test_disjoint_windows_still_wind_down_at_each_close():
    """A lunch break: the morning close is a real close, not an overlap."""
    cfg = _cfg([("08:00", "12:00"), ("13:00", "17:00")])
    assert sessions.should_flatten(cfg, _at(11, 56)) is True
    assert sessions.evaluate(cfg, _at(12, 30)).open is False
    assert sessions.evaluate(cfg, _at(13, 30)).minutes_to_close == 210


def test_outside_every_window_is_still_closed():
    cfg = _cfg(OVERLAP)
    assert sessions.evaluate(cfg, _at(7, 30)).open is False
    assert sessions.evaluate(cfg, _at(18, 0)).open is False
    assert sessions.should_flatten(cfg, _at(18, 0)) is False


def test_a_window_over_midnight_is_unchanged():
    cfg = _cfg([("22:00", "06:00")])
    assert sessions.evaluate(cfg, _at(23, 0)).minutes_to_close == 420
    assert sessions.evaluate(cfg, _at(2, 0)).minutes_to_close == 240
    assert sessions.evaluate(cfg, _at(12, 0)).open is False
