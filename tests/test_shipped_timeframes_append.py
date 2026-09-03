"""Shipped search TFs append onto a stored bag the same way strategies do.

A live blob saved as M15/M30 must pick up a newly shipped M5 on the next
``opt_params()`` read — otherwise soft-restart + merge keeps M5 invisible
forever (Claude 03.09: DB stuck on M15/M30 after M5 was re-shipped).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.store as store_module
from micofx.models import SEARCH_TIMEFRAMES
from micofx.store import Store


def test_shipped_timeframes_append_onto_a_stale_stored_bag(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    st = Store()
    # Simulate the parked-bag era still sitting in settings.
    st.set_setting("opt_params", {"timeframes": ["M15", "M30"]})
    assert "M5" in SEARCH_TIMEFRAMES
    got = st.opt_params()["timeframes"]
    assert got == SEARCH_TIMEFRAMES
    assert "M5" in got
