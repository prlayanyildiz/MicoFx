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
    eng.client = SimpleNamespace(broker_now=lambda: 1_700_000_000.0 + 2 * 3600)
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
