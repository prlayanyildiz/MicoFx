"""The A/B tool measures; it must never write, POST, or touch MT5.

It exists because a grid proposal nearly landed on arithmetic alone, so it is
the thing the next proposal gets checked with - and a measuring tool that can
change the thing it measures is worse than no tool. It reads a snapshot and
the symbol row and runs walk_forward in-process.

Nothing here runs a search: one takes four minutes. The parts that are cheap
to check are checked, and the expensive part is the real ``walk_forward``,
which the rest of this suite already covers.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import ab_search

SRC = Path(ab_search.__file__).read_text(encoding="utf-8")


def test_it_opens_the_database_read_only():
    """The live process owns micofx.db. A tool anyone may run against a live
    book must not be the second writer."""
    assert "mode=ro" in SRC
    assert "?mode=ro" in SRC


def test_it_never_writes_anywhere():
    body = SRC.split('"""', 2)[-1]          # past the module docstring
    for token in ("INSERT", "UPDATE", "DELETE", "commit(",
                  "urllib.request", "set_setting", "update_symbol"):
        assert token not in body, f"olcum araci yaziyor: {token}"


def test_it_never_reaches_mt5():
    """Snapshots exist so this can run with the terminal shut, and a second
    mt5.initialize() is forbidden while the live process holds the terminal."""
    body = SRC.split('"""', 2)[-1]
    assert "mt5.initialize" not in body
    assert "import MetaTrader5" not in body


def test_grid_size_multiplies_the_axes():
    assert ab_search.grid_size({"a": [1, 2, 3], "b": [1, 2]}) == 6
    assert ab_search.grid_size({}) == 1


def test_dropping_an_axis_shrinks_the_grid_and_keeps_the_rest():
    grid = {"a": [1, 2, 3], "b": [1, 2], "c": [1, 2, 3, 4]}
    lean = {k: v for k, v in grid.items() if k not in {"b"}}
    assert ab_search.grid_size(grid) == 24
    assert ab_search.grid_size(lean) == 12
    assert set(lean) == {"a", "c"}


def test_the_docstring_states_the_inheritance_trap():
    """A dropped axis is inherited from the live row, not reset to a default -
    the fact that made the gate-axis proposal lose. Anyone reading a
    --drop-axes result without knowing that will misread it."""
    head = SRC.split('"""')[1]
    assert "from_config" in head
    assert "inherits" in head.lower()


def test_it_refuses_a_symbol_that_is_not_in_the_book():
    import pytest

    with pytest.raises(SystemExit):
        ab_search.live_row("YOKSA-BOYLE-BIR-SEMBOL")
