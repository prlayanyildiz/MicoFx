"""An unsupported timeframe must not be measured in silence.

``_mt5_timeframe`` already warns when it cannot translate a name and falls back
to the default bar. ``timeframe_seconds`` fell back with nothing said, and that
asymmetry is what made the pair dangerous: the name gets fallback bars WITH a
warning, then has its bar arithmetic computed on them WITHOUT one - so every
figure derived from bar length (lookback sizing, hold time in bars, when the
next bar closes) is quietly M5's while the config, the panel and the holdout
all name something else.

05.09: the fallback target moved from M5 (300s) to M30 (1800s) when M5 was
retired, so every literal 300 below became 1800. The warning contract is
unchanged, and is the part that matters.

Found 14.08 while testing whether M1 could be searched. M1 was wired nowhere -
not in the MT5 map, not in this table - so adding it to TIMEFRAMES would have
produced M5 data measured as M1 and reported as a genuine M1 result. M1 was
then wired properly; the guard here uses a name that still is not.

H1 spent a day in this seconds table and the MT5 map after leaving TIMEFRAMES,
so that a live row still naming it kept resolving. None does, and it left both
tables on 15.08, so it now falls back with a warning like any other retired
name. That is the point of the warning: a name in
the table with no warning is "we can still read this bar"; a name in
TIMEFRAMES is "we will search it". ``test_h1_is_not_searchable`` pins the
split. This file still pins "TIMEFRAMES never hits the fallback".
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import mt5client
from micofx.models import TIMEFRAMES

# Bar lengths keyed by name, so the assertion follows TIMEFRAMES instead of
# pinning today's list - H1 moved three times in two days,
# and a literal made that a test edit both times.
_EXPECTED = {"M15": 900, "M30": 1800}

# What an unrecognised name resolves to (M30 since 05.09; was M5/300).
_FALLBACK = 1800


@pytest.fixture(autouse=True)
def _forget_warned():
    mt5client._TF_SECONDS_WARNED.clear()
    yield
    mt5client._TF_SECONDS_WARNED.clear()


def test_every_offered_timeframe_has_a_real_length():
    """Nothing in TIMEFRAMES may reach the fallback."""
    seen = []
    import micofx.mt5client as m
    orig = m.LOG.emit
    m.LOG.emit = lambda msg, level="INFO", symbol="": seen.append(msg)
    try:
        lengths = [mt5client.timeframe_seconds(t) for t in TIMEFRAMES]
    finally:
        m.LOG.emit = orig
    assert seen == [], f"an offered timeframe is not wired: {seen}"
    assert lengths == [_EXPECTED[t] for t in TIMEFRAMES]


def test_an_unwired_name_says_so(monkeypatch):
    seen = []
    monkeypatch.setattr(mt5client.LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append((msg, level)))

    assert mt5client.timeframe_seconds("M3") == _FALLBACK

    assert seen, "the fallback must not be silent"
    msg, level = seen[0]
    assert level == "WARN"
    assert "M3" in msg


def test_it_warns_once_per_name(monkeypatch):
    seen = []
    monkeypatch.setattr(mt5client.LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append(msg))

    for _ in range(5):
        mt5client.timeframe_seconds("M3")

    assert len(seen) == 1, "a poll loop must not flood the log"


def test_m1_is_gone_and_says_so(monkeypatch):
    """Searched 14.08, removed on its numbers - and removed loudly.

    The old half-wired state was dangerous because both fallbacks were silent:
    asking for M1 returned fallback bars measured on fallback arithmetic under
    an M1 label. Both warn now, which is what makes taking the wiring back out
    safe rather than a return to that trap.
    """
    assert "M1" not in TIMEFRAMES

    seen = []
    monkeypatch.setattr(mt5client.LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append((msg, level)))
    assert mt5client.timeframe_seconds("M1") == _FALLBACK
    assert seen and seen[0][1] == "WARN" and "M1" in seen[0][0]


@pytest.mark.parametrize("name,secs", [("m15", 900), ("M15", 900), ("m30", 1800)])
def test_case_is_still_ignored(name, secs, monkeypatch):
    seen = []
    monkeypatch.setattr(mt5client.LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append(msg))
    assert mt5client.timeframe_seconds(name) == secs
    assert seen == []