"""Shipped search TFs union onto a stored bag - which is a resurrection path.

This file used to guarantee the union in M5's favour: "a live blob saved as
M15/M30 must pick up a newly shipped M5 on the next ``opt_params()`` read".
That is still exactly what the code does, but with M5 retired 05.09 the
guarantee reads as an instruction for bringing it back, so the test now states
the mechanism and pins its safety property instead of its convenience.

Why it matters: AGENTS.md claimed reopening a bar needs ``models.TIMEFRAMES``
*and* the stored ``opt_params.timeframes``. It does not. Because the shipped
list is unioned in on every read, editing ``models.TIMEFRAMES`` and
``config/defaults.json`` is sufficient - the stored blob catches up by itself.
Resurrection is a two-file change, and both files are live risk surfaces.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.store as store_module
from micofx.models import SEARCH_TIMEFRAMES
from micofx.store import Store
from tests.retired_lexicon import RETIRED_TIMEFRAMES


def _store(tmp_path, monkeypatch) -> Store:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    return Store()


def test_a_stored_bag_catches_up_with_the_shipped_list(tmp_path, monkeypatch):
    """The union itself: a blob missing a shipped bar gains it on read."""
    st = _store(tmp_path, monkeypatch)
    st.set_setting("opt_params", {"timeframes": ["M30"]})
    assert st.opt_params()["timeframes"] == SEARCH_TIMEFRAMES


def test_a_stored_retired_bar_is_dropped_not_preserved(tmp_path, monkeypatch):
    """The safety half: the union must not resurrect what is stored either.

    A blob written before a retirement still names the retired bar. If
    ``opt_params()`` merged that in, every install that had ever searched M5
    would quietly keep searching it - no file edit, no decision, no trace.
    """
    st = _store(tmp_path, monkeypatch)
    stale = [*RETIRED_TIMEFRAMES, "M15", "M30"]
    st.set_setting("opt_params", {"timeframes": stale})
    got = st.opt_params()["timeframes"]
    for tf in RETIRED_TIMEFRAMES:
        assert tf not in got, f"{tf} stored blob'dan geri geldi: {got}"
    assert got == SEARCH_TIMEFRAMES
