"""Leftover concurrent-risk cap must not warn about a tavan that is unread.

Operator 27.08: the book-wide 1R ceiling left can_open. _note_risk_capacity
compared configured risk% against that leftover number and shouted. With
the gate gone the shout is a lie.
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


def test_leftover_cap_under_a_fatter_book_is_silent(monkeypatch):
    lines = _lines(monkeypatch)
    book = {f"S{i}": _cfg(0.80, 1) for i in range(20)}  # 16% vs leftover 8
    _engine(8.0, book)._note_risk_capacity()
    assert lines == []


def test_size_by_edge_does_not_resurrect_the_notice(monkeypatch):
    lines = _lines(monkeypatch)
    eng = _engine(8.0, BOOK_TODAY)
    eng.store.system.size_by_edge = True
    eng._note_risk_capacity()
    assert lines == []
