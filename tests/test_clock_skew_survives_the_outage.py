"""The broker-vs-machine gap has to outlive the gap it is measured across.

MetaTrader5 exposes no TimeCurrent, so the offset between the broker's wall
clock and this machine's is only measurable while ticks flow. It was held in
memory alone, which meant a restart over a shut market lost it - and the one
reading worth catching is a *change*: the broker shifting an hour at a DST
switch, which happens at 03:00 on a Sunday, inside exactly the outage where
nothing can be measured.

Keeping the last known value across the outage is what lets the first tick
afterwards answer "did the broker move" rather than produce a number with
nothing to compare it against. It stays a cross-check: nothing extrapolates
the broker clock from this machine's, because over a weekend that guess would
be wrong precisely when a DST switch made it matter.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


class _Store:
    def __init__(self, initial=None):
        self.settings = {} if initial is None else dict(initial)

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


def _engine(store, skew_seq):
    eng = object.__new__(Engine)
    eng.store = store
    eng._flush_warned = set()
    eng._session_clock_skew = None
    stored = store.get_setting("session_clock_skew")
    if stored is not None:
        eng._session_clock_skew = int(stored)
    seq = list(skew_seq)
    eng._measured_clock_skew = lambda _now: seq.pop(0) if seq else None
    return eng


def test_an_unmeasurable_clock_does_not_erase_what_was_known(monkeypatch):
    lines: list[tuple[str, str]] = []
    monkeypatch.setattr("micofx.engine.LOG.emit",
                        lambda msg, level="INFO", *a, **k: lines.append((msg, level)))
    store = _Store({"session_clock_skew": 0})
    eng = _engine(store, [None, None])          # shut market, twice

    eng._note_session_clock(0.0)
    eng._note_session_clock(0.0)

    assert eng._session_clock_skew == 0, "olculemeyen saat bilineni silmemeli"
    assert lines == [], "olcum yoksa satir da yok"


def test_the_offset_is_written_so_it_survives_a_restart(monkeypatch):
    monkeypatch.setattr("micofx.engine.LOG.emit", lambda *a, **k: None)
    store = _Store()
    eng = _engine(store, [0])
    eng._note_session_clock(0.0)
    assert store.settings["session_clock_skew"] == 0

    # A fresh process reads it back instead of starting blind.
    again = _engine(store, [])
    assert again._session_clock_skew == 0


def test_a_shift_across_the_outage_is_reported_as_a_shift(monkeypatch):
    """The DST case: measured 0 before the weekend, -1 after."""
    lines: list[tuple[str, str]] = []
    monkeypatch.setattr("micofx.engine.LOG.emit",
                        lambda msg, level="INFO", *a, **k: lines.append((msg, level)))
    store = _Store({"session_clock_skew": 0})
    eng = _engine(store, [None, -1])            # outage, then ticks resume

    eng._note_session_clock(0.0)
    eng._note_session_clock(0.0)

    assert eng._session_clock_skew == -1
    assert store.settings["session_clock_skew"] == -1
    shifted = [m for m, lvl in lines if "broker saati kaydi" in m and lvl == "WARN"]
    assert len(shifted) == 1, "kayma tek satirla bildirilmeli"
    assert "+0 -> -1" in shifted[0]


def test_a_first_ever_reading_reports_the_gap_not_a_shift(monkeypatch):
    """Nothing to compare against yet: the plain warning, not a move."""
    lines: list[tuple[str, str]] = []
    monkeypatch.setattr("micofx.engine.LOG.emit",
                        lambda msg, level="INFO", *a, **k: lines.append((msg, level)))
    eng = _engine(_Store(), [-1])
    eng._note_session_clock(0.0)

    msgs = [m for m, _ in lines]
    assert any("saat farkli" in m for m in msgs)
    assert not any("broker saati kaydi" in m for m in msgs)


def test_a_steady_zero_gap_stays_quiet(monkeypatch):
    lines: list[tuple[str, str]] = []
    monkeypatch.setattr("micofx.engine.LOG.emit",
                        lambda msg, level="INFO", *a, **k: lines.append((msg, level)))
    eng = _engine(_Store({"session_clock_skew": 0}), [0, 0, 0])
    for _ in range(3):
        eng._note_session_clock(0.0)
    assert lines == []
