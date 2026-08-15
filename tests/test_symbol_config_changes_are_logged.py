"""A symbol's risk settings must not change without leaving a record.

Found 13.08 20:00: ``max_positions`` was 5 on all ten symbols while the
dataclass default and config/defaults.json both say 1, and the log could not
say who wrote it - symbol edits emitted nothing at all.

The first fix logged it in web/app.py, which covered only the two panel doors.
Cursor's #065 caught that immediately: at 20:45 the optimizer rewrote strategy,
timeframe and the exit numbers on four symbols (NAS100/XAUUSD/GER40/US500 all
moved to M5) and CFG stayed **empty** - ``Optimizer.apply`` goes straight to
``store.update_symbol``. The audit trail read "nothing changed" while the live
book was being replaced.

So the record now lives on ``Store.update_symbol``: the one choke point every
door goes through - panel patch, bulk patch, optimizer apply/apply_secondary,
and the engine's own pending-exit writes. A new caller cannot get in without
leaving a record.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.logbus import _PERSIST, LOG
from micofx.models import SymbolConfig
from micofx.store import Store


class _FakeStore:
    """Just enough Store to exercise update_symbol's real body."""

    def __init__(self, cfg: SymbolConfig) -> None:
        self.symbols = {cfg.symbol: cfg}
        self.saved: list[SymbolConfig] = []
        import threading
        self._lock = threading.RLock()

    def save_symbol(self, cfg: SymbolConfig) -> None:
        self.saved.append(cfg)
        self.symbols[cfg.symbol] = cfg

    # The methods under test, bound off the real class.
    update_symbol = Store.update_symbol
    _log_symbol_change = Store._log_symbol_change
    _CHANGE_LOG_SKIP = Store._CHANGE_LOG_SKIP


@pytest.fixture
def captured(monkeypatch):
    out: list[dict] = []
    monkeypatch.setattr(LOG, "emit",
                        lambda message, level="INFO", symbol="": out.append(
                            {"message": message, "level": level, "symbol": symbol}))
    return out


def _store(**kw) -> _FakeStore:
    return _FakeStore(SymbolConfig(symbol="NAS100", **kw))


def test_the_record_reaches_disk():
    """An in-memory-only record is gone by the next restart - useless for this."""
    assert "CFG" in _PERSIST


def test_max_positions_change_is_recorded(captured):
    """The field whose provenance could not be established."""
    s = _store(max_positions=1)
    s.update_symbol("NAS100", {"max_positions": 5}, source="panel")

    assert len(captured) == 1
    msg = captured[0]["message"]
    assert "max_positions" in msg and "1" in msg and "5" in msg
    assert captured[0]["level"] == "CFG"
    assert captured[0]["symbol"] == "NAS100"
    assert "panel" in msg


def test_the_optimizer_door_is_recorded(captured):
    """The exact gap Cursor #065 found: the book changed, CFG was silent."""
    s = _store(strategy="st_trend", timeframe="M15")
    s.update_symbol("NAS100", {"strategy": "t3_stoch", "timeframe": "M5"},
                    source="opt apply")

    assert len(captured) == 1
    msg = captured[0]["message"]
    assert "opt apply" in msg, "the door that changed the book must be named"
    assert "strategy" in msg and "timeframe" in msg
    assert "M15" in msg and "M5" in msg


def test_an_unnamed_caller_still_leaves_a_record(captured):
    """A future call site that forgets `source` must not become invisible."""
    s = _store(max_positions=1)
    s.update_symbol("NAS100", {"max_positions": 5})
    assert len(captured) == 1
    assert "bilinmeyen" in captured[0]["message"]


def test_exit_risk_numbers_are_reported(captured):
    s = _store(sl_atr_mult=1.0, trail_start_atr=0.5, trail_step_atr=2.2)
    s.update_symbol("NAS100", {"sl_atr_mult": 0.9, "trail_step_atr": 0.8},
                    source="opt apply")

    msg = captured[0]["message"]
    assert "sl_atr_mult" in msg and "trail_step_atr" in msg
    assert "trail_start_atr" not in msg, "unchanged field must not be reported"


def test_an_unchanged_field_is_not_reported(captured):
    s = _store(max_positions=5)
    s.update_symbol("NAS100", {"max_positions": 5}, source="panel")
    assert captured == []


def test_summary_blobs_and_their_timestamps_are_not_reported(captured):
    """These change on every apply and drown the fields being audited."""
    s = _store(max_positions=1)
    s.update_symbol("NAS100", {
        "max_positions": 5,
        "opt_summary": {"anything": 1},
        "opt_updated_at": 12345.0,
    }, source="opt apply")

    msg = captured[0]["message"]
    assert "max_positions" in msg
    for noisy in ("opt_summary", "opt_updated_at"):
        assert noisy not in msg


def test_a_missing_symbol_makes_no_record(captured):
    s = _store()
    assert s.update_symbol("YOKSA", {"max_positions": 5}, source="panel") is None
    assert captured == []


def test_every_caller_names_its_door():
    """The point of the choke point: no unnamed writer in the codebase."""
    import re

    root = Path(__file__).resolve().parents[1] / "micofx"
    unnamed = []
    for path in root.rglob("*.py"):
        if path.name == "store.py":
            continue
        # Comments name the method too ("... goes through store.update_symbol(),
        # unvalidated") - strip them so prose is not read as a call site.
        text = "\n".join(re.sub(r"#.*$", "", line) for line in
                         path.read_text(encoding="utf-8").splitlines())
        for m in re.finditer(r"update_symbol\((?:[^()]|\([^()]*\))+\)", text, re.S):
            if "source=" not in m.group(0):
                unnamed.append(f"{path.name}: {m.group(0)[:70]}")
    assert not unnamed, "these writers leave an unattributable record: " + "; ".join(unnamed)
