"""M10 and H4 are gone, and an unknown bar no longer resolves in silence.

Both were kept alive in translation tables long after they stopped being
offered, so that a config stored while they existed would still resolve to the
right MT5 constant and the right number of seconds. That was the correct call
while such a config might exist. None does: every stored symbol row uses one of
TIMEFRAMES, and the only remaining mention anywhere in the database was a stale
``opt_params.strategy_timeframes`` blob that named M10 for micro_rev and burst -
inert, because the search never asks about a bar outside TIMEFRAMES, and now
filtered out on read.

Deleting the entries alone would have left the real hazard standing, which was
never M10 itself: ``timeframe_const`` falls back to M5 for anything it does not
recognise, so an unrecognised timeframe means a symbol quietly trading
five-minute bars instead of the ones it was validated on. That fallback stays -
refusing to resolve would take the engine down over one bad row - but it now
says so out loud instead of looking like a normal resolution.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import mt5client
from micofx.models import TIMEFRAMES, uses_swing_exits

RETIRED = ("M1", "M10", "M20", "H2", "H4", "D1", "W1", "MN1")


# ------------------------------------------------------ nothing resolves them

@pytest.mark.parametrize("name", RETIRED)
def test_a_retired_timeframe_is_not_translated_to_seconds(name):
    """models.uses_swing_exits' own table used to carry M10 and H4."""
    assert uses_swing_exits("t3_stoch", name) is False


@pytest.mark.parametrize("name", RETIRED)
def test_a_retired_timeframe_has_no_second_count(name):
    assert mt5client.timeframe_seconds(name) == 300, "taninmayan bar M5'e dusmeli"


def test_the_offered_timeframes_still_translate():
    assert [mt5client.timeframe_seconds(t) for t in TIMEFRAMES] == [300, 900, 1800, 3600]
    for tf in TIMEFRAMES:
        assert uses_swing_exits("t3_stoch", tf) is (tf != "M5")


# ------------------------------------- the tables themselves carry no leftovers

def _tables(source: str) -> list[str]:
    """Every dict literal that maps timeframe names to something."""
    return re.findall(r"\{[^{}]*\"M5\"\s*:[^{}]*\}", source, re.S)


@pytest.mark.parametrize("module", ["models", "mt5client"])
def test_no_timeframe_table_still_lists_a_retired_bar(module):
    source = (Path(__file__).resolve().parents[1] / "micofx" / f"{module}.py").read_text(
        encoding="utf-8")
    for table in _tables(source):
        named = set(re.findall(r"\"([A-Z]+\d+)\"", table))
        leftover = named - set(TIMEFRAMES)
        assert not leftover, f"{module}.py tablosunda kalinti: {sorted(leftover)}"


def test_at_least_one_table_was_actually_found():
    """Guards the regex above from passing by matching nothing."""
    source = (Path(__file__).resolve().parents[1] / "micofx" / "mt5client.py").read_text(
        encoding="utf-8")
    assert _tables(source), "tablo bulunamadi - test bos calisiyor"


# --------------------------------------- an unknown bar is no longer silent

def test_an_unknown_timeframe_reports_itself(monkeypatch):
    said: list[tuple] = []
    monkeypatch.setattr(mt5client.LOG, "emit",
                        lambda msg, level="INFO", symbol="": said.append((msg, level)))
    mt5client.timeframe_const("M10")
    assert said, "taninmayan zaman dilimi sessizce M5'e dustu"
    msg, level = said[0]
    assert "M10" in msg and level in ("WARN", "ERROR")


def test_a_known_timeframe_says_nothing(monkeypatch):
    said: list[tuple] = []
    monkeypatch.setattr(mt5client.LOG, "emit",
                        lambda msg, level="INFO", symbol="": said.append((msg, level)))
    for tf in TIMEFRAMES:
        mt5client.timeframe_const(tf)
    assert not said, "gecerli zaman dilimi gurultu uretiyor"
