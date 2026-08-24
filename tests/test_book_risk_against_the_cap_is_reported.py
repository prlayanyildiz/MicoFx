"""A book configured to want more risk than the cap allows must say so.

The concurrent-risk cap is enforced one entry at a time and it refuses.
Nothing compared the book's own arithmetic against it beforehand, so a
portfolio asking for more than the ceiling did not fail - it degraded.
Entries fill until the ceiling is reached and are refused afterwards, which
hands the room to whichever symbol signals first and takes the selector's
ranking out of the decision. The refusal reads like an ordinary condition in
the log, which is what makes it worth announcing in advance.

Two ways in. Raising slots is the visible one: five symbols at three slots
plus gold is 12.8 percent under a 15 percent cap, and five slots would be 24.
The quiet one is a fallback - the shipped and dataclass defaults for the cap
are 8.0, sized for a freshly seeded book at one slot each, so a system row
that falls back to defaults while the symbol rows survive puts an 8 percent
cap under a 12.8 percent book. That is the same shape as max_total_positions
defaulting below the book it guards.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


def _cfg(risk, slots, enabled=True):
    return types.SimpleNamespace(risk_percent=risk, max_positions=slots, enabled=enabled)


def _engine(cap, symbols):
    eng = object.__new__(Engine)
    eng._flush_warned = set()
    eng._risk_capacity_noted = None
    eng.store = types.SimpleNamespace(
        system=types.SimpleNamespace(max_concurrent_risk_pct=cap),
        symbols=symbols)
    return eng


BOOK_TODAY = {f"S{i}": _cfg(0.80, 3) for i in range(5)} | {"XAUUSD": _cfg(0.80, 1)}


def _lines(monkeypatch):
    out: list[tuple[str, str]] = []
    monkeypatch.setattr("micofx.engine.LOG.emit",
                        lambda msg, level="INFO", *a, **k: out.append((msg, level)))
    return out


def test_todays_book_under_todays_cap_is_silent(monkeypatch):
    """12.8 under 15 - configured deliberately, nothing to say."""
    lines = _lines(monkeypatch)
    _engine(15.0, BOOK_TODAY)._note_risk_capacity()
    assert lines == []


def test_size_by_edge_raises_the_configured_ceiling(monkeypatch):
    """Live flag. EDGE_MAX 2.2 turns 12.8 into 28.16, above the 15 cap."""
    lines = _lines(monkeypatch)
    eng = _engine(15.0, BOOK_TODAY)
    eng.store.system.size_by_edge = True
    eng._note_risk_capacity()
    warned = [m for m, lvl in lines if lvl == "WARN" and "eszamanli risk" in m]
    assert len(warned) == 1
    assert "%28.16" in warned[0] and "%15.00" in warned[0]


def test_the_default_cap_under_todays_book_is_reported(monkeypatch):
    """The quiet path: system settings fall back while the symbols survive."""
    lines = _lines(monkeypatch)
    _engine(8.0, BOOK_TODAY)._note_risk_capacity()
    warned = [m for m, lvl in lines if lvl == "WARN" and "eszamanli risk" in m]
    assert len(warned) == 1
    assert "%12.80" in warned[0] and "%8.00" in warned[0]


def test_raising_slots_past_the_cap_is_reported(monkeypatch):
    lines = _lines(monkeypatch)
    book = {f"S{i}": _cfg(0.80, 5) for i in range(6)}      # 24%
    _engine(15.0, book)._note_risk_capacity()
    assert any("%24.00" in m for m, _ in lines)


def test_a_disabled_symbol_does_not_count(monkeypatch):
    lines = _lines(monkeypatch)
    book = dict(BOOK_TODAY) | {"OFF": _cfg(0.80, 10, enabled=False)}
    _engine(15.0, book)._note_risk_capacity()
    assert lines == [], "kapali sembol nominal riske girmemeli"


def test_it_speaks_once_and_again_only_on_a_change(monkeypatch):
    lines = _lines(monkeypatch)
    eng = _engine(8.0, BOOK_TODAY)
    eng._note_risk_capacity()
    eng._note_risk_capacity()
    assert len(lines) == 1, "sabit yapilandirma sessiz kalmali"

    eng.store.system.max_concurrent_risk_pct = 20.0     # now it fits
    eng._note_risk_capacity()
    assert len(lines) == 1, "tavan yeterliyken satir yok"

    eng.store.system.max_concurrent_risk_pct = 8.0      # and back
    eng._note_risk_capacity()
    assert len(lines) == 2, "degisiklik yeniden konusur"


def test_a_cap_of_zero_means_no_cap(monkeypatch):
    lines = _lines(monkeypatch)
    _engine(0.0, BOOK_TODAY)._note_risk_capacity()
    assert lines == []
