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
never M10 itself: ``timeframe_const`` falls back for anything it does not
recognise, so an unrecognised timeframe means a symbol quietly trading a bar it
was not validated on. That fallback stays - refusing to resolve would take the
engine down over one bad row - but it now says so out loud instead of looking
like a normal resolution.

05.09: the fallback target moved from M5 to M30 with the M5 retirement, so the
"falls back to 300 seconds" assertions below moved with it. The fallback is
still the *slowest* legal bar rather than the fastest, which is the safer
direction: a misresolved row now over-holds instead of over-trading.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import mt5client
from micofx.models import READABLE_TIMEFRAMES, TIMEFRAMES, uses_swing_exits

# Bar lengths keyed by name, so the assertion follows TIMEFRAMES instead of
# pinning today's list - H1 left the search on 14.08, came back on 15.08 and
# left again the same evening, and a literal made that a test edit each time.
_EXPECTED = {"M15": 900, "M30": 1800}

# What an unrecognised bar resolves to. Named once so a future change to the
# fallback is a one-line edit here rather than eleven scattered literals.
_FALLBACK_SECONDS = 1800

# M1 rejoined this list 14.08: wired and searched, then removed on its numbers.
# H1 is here for the third time and, unlike the first, on a measurement; it was
# re-measured 05.09 under the corrected replay and lost 6/6 symbols on R/day.
# M5 joined 05.09: 0/7 symbols would pick it, five outright negative, at
# +6-32% cost per trade. Nothing in the book is hourly or five-minute.
RETIRED = ("M1", "M3", "M5", "H1", "M10", "M20", "H2", "H4", "D1", "W1", "MN1")

# A family that actually exists. This used to be "stoch_flip", which was
# retired 01.09 - the assertions still passed (a retired name resolves the same
# way) but the file read as though that family were live.
_LIVE_FAMILY = "burst"


# ------------------------------------------------------ nothing resolves them

@pytest.mark.parametrize("name", RETIRED)
def test_a_retired_timeframe_is_not_translated_to_seconds(name):
    """models.uses_swing_exits' own table used to carry M10 and H4."""
    assert uses_swing_exits(_LIVE_FAMILY, name) is False


@pytest.mark.parametrize("name", RETIRED)
def test_a_retired_timeframe_has_no_second_count(name):
    assert mt5client.timeframe_seconds(name) == _FALLBACK_SECONDS, (
        "taninmayan bar en yavas yasal bara (M30) dusmeli")


def test_the_offered_timeframes_still_translate():
    assert ([mt5client.timeframe_seconds(t) for t in TIMEFRAMES]
            == [_EXPECTED[t] for t in TIMEFRAMES])
    # This used to read ``is (tf != "M5")``. With M5 retired that expression is
    # always True, so the assertion stopped distinguishing anything while still
    # passing - it looked like a live either/or and tested nothing. Stated
    # plainly instead: every remaining bar is a swing bar, so the wider exit
    # envelope applies to all of them. See uses_swing_exits' own docstring.
    for tf in TIMEFRAMES:
        assert uses_swing_exits(_LIVE_FAMILY, tf) is True


# ------------------------------------- the tables themselves carry no leftovers

def _tables(source: str) -> list[str]:
    """Every dict literal that maps timeframe names to something.

    Anchored on a bar that is actually still shipped. This was anchored on
    ``"M5"`` until 05.09; when M5 left the tables the regex matched nothing and
    ``test_no_timeframe_table_still_lists_a_retired_bar`` began passing
    vacuously for both modules. It was ``test_at_least_one_table_was_actually_found``
    below that caught it - which is the whole reason that companion exists, and
    why it should survive any future edit to this pattern.
    """
    return re.findall(r"\{[^{}]*\"M30\"\s*:[^{}]*\}", source, re.S)


@pytest.mark.parametrize("module", ["models", "mt5client"])
def test_no_timeframe_table_still_lists_a_retired_bar(module):
    source = (Path(__file__).resolve().parents[1] / "micofx" / f"{module}.py").read_text(
        encoding="utf-8")
    for table in _tables(source):
        named = set(re.findall(r"\"([A-Z]+\d+)\"", table))
        leftover = named - set(READABLE_TIMEFRAMES)
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


# ------------------------------------- nothing configurable names one of them

def _retired_in(text: str) -> set[str]:
    """Quoted timeframe-looking tokens that are not one of the four."""
    named = set(re.findall(r"[\"']([A-Z]{1,2}\d{1,2})[\"']", text))
    return named - set(TIMEFRAMES)


def test_the_shipped_defaults_name_no_other_timeframe():
    text = (Path(__file__).resolve().parents[1] / "config" / "defaults.json").read_text(
        encoding="utf-8")
    assert not _retired_in(text) & set(RETIRED), sorted(_retired_in(text) & set(RETIRED))


def test_the_panel_offers_no_other_timeframe():
    js = Path(__file__).resolve().parents[1] / "micofx" / "web" / "static" / "app.js"
    if not js.exists():
        pytest.skip("panel bulunamadi")
    text = js.read_text(encoding="utf-8")
    assert not _retired_in(text) & set(RETIRED), sorted(_retired_in(text) & set(RETIRED))


def test_no_stored_symbol_names_one_of_them():
    """The live book, asserted rather than assumed."""
    import json
    import sqlite3
    db = Path(__file__).resolve().parents[1] / "data" / "micofx.db"
    if not db.exists():
        pytest.skip("canli veritabani yok")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = [json.loads(r[0]) for r in con.execute("SELECT payload FROM symbols")]
    finally:
        con.close()
    assert rows, "sembol yok - test bos calisiyor"
    for cfg in rows:
        for field in ("timeframe", "secondary_timeframe"):
            value = cfg.get(field) or ""
            assert value == "" or value in TIMEFRAMES, (
                f"{cfg.get('symbol')}.{field} = {value!r}")
