"""A flat book that went stale must still poll ticks, or the clock never recovers.

27.08 00:00 restart seeded broker_now from 23:58:59, then the 60s pace
window expired with the book not ticking. _evaluate returns before
client.tick() when decision_now is None, and a flat book never reaches
_update_stop either. 04:39: six symbols still 'broker saati bayat',
panel CALISIYOR/BAGLI, log empty, 8400 cycles. The gate (do not trade)
is right. Never calling tick() again is the deadlock.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


def _cycle_src() -> str:
    src = Path("micofx/engine.py").read_text(encoding="utf-8")
    return src.split("def _cycle(", 1)[1].split("\n    def ", 1)[0]


def test_the_cycle_probes_ticks_before_decision_now():
    cycle = _cycle_src()
    probe_at = cycle.find("_probe_book_ticks")
    gate_at = cycle.find("decision_now")
    assert probe_at != -1, (
        "dongu tick okumuyor - duz kitap donunca saat bir daha ilerlemez")
    assert gate_at != -1
    assert probe_at < gate_at, (
        "tick kapidan sonra - evaluate donunce probe'a hic gelinmez")
    probe_src = Path("micofx/engine.py").read_text(encoding="utf-8")
    probe_body = probe_src.split("def _probe_book_ticks", 1)[1].split("\n    def ", 1)[0]
    assert "force=True" in probe_body, "probe cache'i bayat tick'i tekrar etmemeli"


def test_a_stale_clock_is_warned_once_not_every_cycle(monkeypatch):
    """8325 silent cycles was the incident. One WARN per 15 min, not per poll."""
    emitted: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "micofx.engine.LOG.emit",
        lambda msg, level="INFO", symbol="": emitted.append((level, msg)))

    class _Client:
        def broker_now(self):
            return 1.0

    eng = Engine.__new__(Engine)
    eng.client = _Client()
    eng.cycle_count = 40
    eng._clock_stale_warned_at = 0.0
    eng._note_stale_decision_clock(None)
    eng._note_stale_decision_clock(None)
    warns = [m for level, m in emitted if level == "WARN"]
    assert len(warns) == 1, warns
    assert "broker saati bayat" in warns[0]


def test_the_first_minute_after_restart_stays_quiet(monkeypatch):
    """The 60s unknown window is still not a fault."""
    emitted: list[str] = []
    monkeypatch.setattr(
        "micofx.engine.LOG.emit",
        lambda msg, level="INFO", symbol="": emitted.append(msg))
    eng = Engine.__new__(Engine)
    eng.client = object()
    eng.cycle_count = 5
    eng._clock_stale_warned_at = 0.0
    eng._note_stale_decision_clock(None)
    assert emitted == []
