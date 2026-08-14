"""Re-adding a name must not inherit the deleted instrument's record.

Deleting a symbol left two things in memory keyed by its name: the supervisor's
verdict - with its evidence epoch and probation flag - and the engine's
entry-block tally. Add a symbol under the same name and the fresh instrument
opens carrying a suspension and a set of block counts it never earned. That is
the "judge B by A's record" failure the supervisor spends most of its length
avoiding, arriving through the one door that does not go through the supervisor.

``clear()`` keeps the verdict row on purpose: an operator releasing a symbol
needs the release epoch to survive the next review. Deletion is the opposite
case and needs the row gone, so it is a separate call.

The tally was pruned against the live book on flush, which only helps while the
name is absent - re-add before the next flush and the counters come back.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.supervisor import Supervisor, SymbolVerdict


def _supervisor() -> Supervisor:
    sup = Supervisor.__new__(Supervisor)
    sup._lock = threading.RLock()
    sup.verdicts = {}
    return sup


def test_forget_drops_the_verdict_outright():
    sup = _supervisor()
    v = SymbolVerdict(symbol="EURUSD", state="quarantine", reason="PF 0.31")
    v.history_cleared_at = 1786751699.0
    v.probation = True
    sup.verdicts["EURUSD"] = v

    sup.forget("EURUSD")

    assert "EURUSD" not in sup.verdicts, (
        "a new symbol under this name would inherit the suspension and its epoch")


def test_forgetting_an_unknown_symbol_is_harmless():
    sup = _supervisor()
    sup.forget("YOKSA")           # must not raise
    assert sup.verdicts == {}


def test_forget_leaves_other_symbols_alone():
    sup = _supervisor()
    sup.verdicts = {"A": SymbolVerdict(symbol="A"), "B": SymbolVerdict(symbol="B")}
    sup.forget("A")
    assert set(sup.verdicts) == {"B"}


def test_clear_still_keeps_the_row_for_a_release():
    """The two calls exist because they answer different questions."""
    import inspect

    doc = inspect.getdoc(Supervisor.clear) or ""
    assert "epoch" in doc.lower(), (
        "clear() keeps the row so a release survives the next review")
    assert "pop" not in inspect.getsource(Supervisor.clear).split("def clear")[1][:600]


def _engine_with_tally(tally: dict) -> Engine:
    eng = Engine.__new__(Engine)
    eng._entry_blocks = tally
    eng._entry_blocks_dirty = False
    eng._flush_entry_blocks = lambda: None       # type: ignore[assignment]
    return eng


def test_the_entry_tally_is_dropped_at_delete_not_at_the_next_flush():
    eng = _engine_with_tally({"EURUSD": {"primary": {"attempts": {"spread": 4}}},
                              "NAS100": {"primary": {"attempts": {"spread": 1}}}})
    eng.forget_entry_blocks("EURUSD")
    assert set(eng._entry_blocks) == {"NAS100"}
    assert eng._entry_blocks_dirty is True, "the drop has to reach disk"


def test_forgetting_a_tally_that_is_not_there_does_not_dirty_the_blob():
    eng = _engine_with_tally({"NAS100": {}})
    eng.forget_entry_blocks("EURUSD")
    assert eng._entry_blocks_dirty is False


def test_delete_calls_both():
    """Either one left out is a route back to inheriting the old record."""
    app = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py").read_text(
        encoding="utf-8")
    body = app[app.index("def remove_symbol"):]
    body = body[:body.index("@app.get")]
    assert "engine.supervisor.forget(symbol)" in body
    assert "engine.forget_entry_blocks(symbol)" in body
    assert "engine.supervisor.clear(symbol)" not in body, (
        "clear() keeps the row; deletion needs it gone")
