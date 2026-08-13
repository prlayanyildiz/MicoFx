"""A symbol's risk settings must not change without leaving a record.

Found 13.08 20:00: ``max_positions`` was 5 on all ten symbols, while the
dataclass default (models.py) and config/defaults.json both say 1 and
claude/GERI_ALMA_max_positions.json records the previous value as 10. Nothing
in micofx/ writes the field - risk.py only reads it, the optimizer never
touches it - so it can only have arrived through the panel. The log could not
confirm that, because symbol edits emitted nothing at all: AI settings changes
log, symbol config changes did not.

Without this record, rule 11 (catch a silent write-back in the same round)
cannot be applied to symbol settings at all - there is nothing to look at.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.logbus import LOG, _PERSIST
from micofx.models import SymbolConfig
from micofx.web.app import _log_symbol_change


@pytest.fixture
def captured(monkeypatch):
    out: list[dict] = []
    monkeypatch.setattr(LOG, "emit",
                        lambda message, level="INFO", symbol="": out.append(
                            {"message": message, "level": level, "symbol": symbol}))
    return out


def _cfg(**kw) -> SymbolConfig:
    return SymbolConfig(symbol="SpotBrent", **kw)


def test_a_max_positions_change_is_recorded(captured):
    """The exact field whose provenance could not be established."""
    _log_symbol_change("SpotBrent", _cfg(max_positions=1), _cfg(max_positions=5), "panel")

    assert len(captured) == 1
    entry = captured[0]
    assert "max_positions" in entry["message"]
    assert "1" in entry["message"] and "5" in entry["message"]
    assert entry["symbol"] == "SpotBrent"
    assert "panel" in entry["message"], "the door used must be named"


def test_the_record_reaches_disk():
    """An in-memory-only record is gone by the next restart - useless for this."""
    assert "CFG" in _PERSIST


def test_the_source_distinguishes_the_doors(captured):
    _log_symbol_change("SpotBrent", _cfg(max_positions=1), _cfg(max_positions=5), "toplu")
    assert "toplu" in captured[0]["message"]


def test_an_unchanged_field_is_not_reported(captured):
    """Submitting a field at its existing value is not a change."""
    _log_symbol_change("SpotBrent", _cfg(max_positions=5), _cfg(max_positions=5), "panel")
    assert captured == []


def test_several_changed_fields_are_all_named(captured):
    _log_symbol_change("SpotBrent",
                       _cfg(max_positions=1, risk_percent=0.5),
                       _cfg(max_positions=5, risk_percent=1.25), "panel")

    assert len(captured) == 1
    assert "max_positions" in captured[0]["message"]
    assert "risk_percent" in captured[0]["message"]


def test_it_diffs_what_landed_not_what_was_asked_for(captured):
    """A field the store coerced or ignored must read as what actually landed.

    Echoing the request would have reported a write that never happened - the
    precise failure mode that makes an audit trail worse than none.
    """
    _log_symbol_change("SpotBrent", _cfg(max_positions=1), _cfg(max_positions=1), "panel")
    assert captured == []


def test_a_missing_side_is_not_reported_as_a_change(captured):
    """404 / not-found paths must not manufacture a phantom record."""
    _log_symbol_change("SpotBrent", None, _cfg(max_positions=5), "panel")
    _log_symbol_change("SpotBrent", _cfg(max_positions=5), None, "panel")
    assert captured == []
