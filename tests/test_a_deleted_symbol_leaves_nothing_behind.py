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


def _engine_with_ratio(ratio: dict):
    eng = Engine.__new__(Engine)
    eng._spread_ratio = ratio
    eng._spread_ratio_dirty = False
    eng._spread_ratio_at = 1.0
    eng._flush_spread_ratio = lambda *a, **k: None    # type: ignore[assignment]
    return eng


def test_the_spread_histogram_goes_at_delete_not_at_the_next_flush():
    """The flush prunes it, but only every five minutes.

    Found 15.08 after the operator deleted LTCUSD and ADAUSD: both were gone
    from the book, opt_runs, verdicts, engine state and the capacity table, and
    still present under settings.spread_ratio. _spread_scale looks that
    histogram up by name, so a symbol re-added inside the window would have been
    searched against a dead one's spread distribution.
    """
    eng = _engine_with_ratio({"LTCUSD": [1, 2], "NAS100": [3, 4]})
    eng.forget_spread_ratio("LTCUSD")
    assert set(eng._spread_ratio) == {"NAS100"}
    assert eng._spread_ratio_dirty is True
    assert eng._spread_ratio_at == 0.0, "the throttle has to be bypassed once"


def test_forgetting_a_histogram_that_is_not_there_changes_nothing():
    eng = _engine_with_ratio({"NAS100": [3, 4]})
    eng.forget_spread_ratio("LTCUSD")
    assert eng._spread_ratio_dirty is False


def test_delete_calls_the_histogram_drop_too():
    app = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py").read_text(
        encoding="utf-8")
    body = app[app.index("def remove_symbol"):]
    body = body[:body.index("@app.get")]
    assert "engine.forget_spread_ratio(symbol)" in body


def test_the_filled_bar_record_goes_at_delete_too():
    """Fourth of four. Keyed by name, so a re-add inherits "already traded".

    Found 15.08 after the perpetuals were deleted: book, opt_runs, verdicts,
    engine state, entry tally and spread histogram were all clean, and
    settings.filled_bars still held BRENTOIL-PERP.
    """
    eng = Engine.__new__(Engine)
    eng._filled_bars = {"BRENTOIL-PERP": {"primary": 123}, "NAS100": {"primary": 9}}
    written = {}
    eng.store = type("S", (), {"set_setting": lambda self, k, v: written.update({k: v})})()
    eng.forget_filled_bars("BRENTOIL-PERP")
    assert set(eng._filled_bars) == {"NAS100"}
    assert written.get("filled_bars") == eng._filled_bars


def test_delete_drops_all_four_name_keyed_records():
    """Verdict, entry tally, spread histogram, filled bars - the whole set."""
    app = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py").read_text(
        encoding="utf-8")
    body = app[app.index("def remove_symbol"):]
    body = body[:body.index("@app.get")]
    for call in ("engine.supervisor.forget(symbol)", "engine.forget_entry_blocks(symbol)",
                 "engine.forget_spread_ratio(symbol)", "engine.forget_filled_bars(symbol)"):
        assert call in body, call
