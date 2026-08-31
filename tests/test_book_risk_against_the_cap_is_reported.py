"""Leftover concurrent-risk cap must not warn about a tavan that is unread.

Operator 27.08: the book-wide 1R ceiling left ``can_open``. ``_note_risk_capacity``
compared configured risk% against that leftover number and shouted. With the
gate gone the shout is a lie, so the method was reduced to a bare ``return``
and this file pinned the silence.

31.08: a method whose entire body is ``return``, called unconditionally every
cycle, is not silence - it is a call site that reads as if something still
checks the cap. Both are gone, and the guard is now structural: the leftover
field must have no reader on the engine's cycle path at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine

SOURCE = (Path(__file__).resolve().parents[1] / "micofx" / "engine.py").read_text(
    encoding="utf-8")


def test_the_no_op_notice_is_gone():
    assert not hasattr(Engine, "_note_risk_capacity")
    assert "_note_risk_capacity" not in SOURCE
    assert "_risk_capacity_noted" not in SOURCE


def test_the_leftover_cap_is_still_not_read_as_a_gate():
    """It may appear in a comment explaining that it is unread; it must not
    appear as an attribute access the cycle acts on."""
    assert "system.max_concurrent_risk_pct" not in SOURCE


def test_the_engine_still_exposes_the_notices_that_do_something():
    for name in ("_note_stale_decision_clock", "_note_session_clock",
                 "_note_unmanaged_ticket"):
        assert callable(getattr(Engine, name)), name
