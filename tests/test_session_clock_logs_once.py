"""The October split must hit the log, not only a JSON field."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.sessions import session_clock_warning


def test_engine_logs_when_skew_appears(monkeypatch):
    lines: list[str] = []
    eng = Engine.__new__(Engine)
    eng._session_clock_skew = None
    # A fresh reading. Without an age the stamp could be Friday's close, and
    # the engine refuses to call that a timezone change - see
    # test_stale_broker_clock_does_not_warn.
    eng.client = SimpleNamespace(broker_now=lambda: 1_700_000_000.0 + 2 * 3600,
                                 broker_now_age=lambda: 5.0)
    monkeypatch.setattr("micofx.engine.LOG.emit",
                        lambda msg, level="INFO", symbol="": lines.append(msg))
    monkeypatch.setattr(
        "micofx.sessions.session_clock_skew_hours",
        lambda *a, **k: -1,
    )
    Engine._note_session_clock(eng, 1_700_000_000.0)
    assert any("saat farkli" in m for m in lines)
    lines.clear()
    Engine._note_session_clock(eng, 1_700_000_000.0)
    assert lines == []  # same skew is not re-logged
    assert session_clock_warning(-1)


def test_a_stale_reading_logs_nothing(monkeypatch):
    """The weekend case: a two-day-old stamp is not a timezone change.

    Guards the log itself, not just the helper. Before the age gate this path
    wrote "broker saati yerel saatten -42 saat farkli" every cycle from Friday
    close to Sunday open, which is exactly loud enough to hide the real
    one-hour drift when October brings it.
    """
    lines: list[str] = []
    eng = Engine.__new__(Engine)
    eng._session_clock_skew = None
    eng.client = SimpleNamespace(broker_now=lambda: 1_700_000_000.0 - 40 * 3600,
                                 broker_now_age=lambda: 40 * 3600.0)
    monkeypatch.setattr("micofx.engine.LOG.emit",
                        lambda msg, level="INFO", symbol="": lines.append(msg))
    Engine._note_session_clock(eng, 1_700_000_000.0)
    assert lines == []
