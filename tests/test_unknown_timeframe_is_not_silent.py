"""An unsupported timeframe must not be measured as M5 in silence.

``_mt5_timeframe`` already warns when it cannot translate a name and falls back
to M5 bars. ``timeframe_seconds`` fell back to 300 with nothing said, and that
asymmetry is what made the pair dangerous: the name gets M5 bars WITH a
warning, then has its bar arithmetic computed as M5 WITHOUT one - so every
figure derived from bar length (lookback sizing, hold time in bars, when the
next bar closes) is quietly M5's while the config, the panel and the holdout
all name something else.

Found 14.08 while testing whether M1 could be searched. M1 was wired nowhere -
not in the MT5 map, not in this table - so adding it to TIMEFRAMES would have
produced M5 data measured as M1 and reported as a genuine M1 result. M1 was
then wired properly; the guard here uses a name that still is not.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import mt5client
from micofx.models import TIMEFRAMES


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
    assert lengths == [60, 300, 900, 1800, 3600]


def test_an_unwired_name_says_so(monkeypatch):
    seen = []
    monkeypatch.setattr(mt5client.LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append((msg, level)))

    assert mt5client.timeframe_seconds("M3") == 300

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


def test_m1_is_wired_now_that_it_is_offered():
    """The middle state was the fault: offered but unwired, or neither."""
    assert "M1" in TIMEFRAMES
    assert mt5client.timeframe_seconds("M1") == 60


@pytest.mark.parametrize("name,secs", [("m5", 300), ("M15", 900), ("h1", 3600)])
def test_case_is_still_ignored(name, secs, monkeypatch):
    seen = []
    monkeypatch.setattr(mt5client.LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append(msg))
    assert mt5client.timeframe_seconds(name) == secs
    assert seen == []
