"""entry_blocks_cumulative — reset/roll immune all-time ledger (operator 04.09)."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

from micofx.engine import ENTRY_BLOCKS_ROLL_SEC, Engine


class _Store:
    def __init__(self):
        self.saved: dict = {}
        self.symbols = {"X": object()}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)

    def set_setting(self, key, value):
        self.saved[key] = value


def _bare_engine(store: _Store | None = None) -> Engine:
    eng = Engine.__new__(Engine)
    eng.store = store or _Store()
    eng.client = MagicMock()
    eng._entry_blocks = {}
    eng._entry_blocks_since = time.time()
    eng._entry_blocks_dirty = False
    eng._entry_blocks_cum = {}
    eng._entry_blocks_cum_since = time.time()
    eng._entry_blocks_cum_dirty = False
    eng._entry_last_bar = {}
    eng._entry_events = []
    eng._entry_events_dirty = False
    eng._entry_event_limit = 100
    eng._entry_blocks_flushed_at = 0.0
    eng._flush_ok = lambda *a, **k: None
    eng._flush_failed = lambda *a, **k: None
    eng._record_entry_event = lambda *a, **k: None
    return eng


def test_tally_writes_rolling_and_cumulative():
    eng = _bare_engine()
    eng._tally_entry("X", "spread", bar_key=("m15", 1))
    eng._tally_entry("X", "spread", bar_key=("m15", 1))  # retry same episode
    assert eng._entry_blocks["X"]["primary"]["signals"]["spread"] == 1
    assert eng._entry_blocks["X"]["primary"]["attempts"]["spread"] == 2
    assert eng._entry_blocks_cum["X"]["primary"]["signals"]["spread"] == 1
    assert eng._entry_blocks_cum["X"]["primary"]["attempts"]["spread"] == 2


def test_roll_and_reset_leave_cumulative():
    eng = _bare_engine()
    eng._tally_entry("X", "spread", bar_key=("m15", 1))
    eng._entry_blocks_since = time.time() - ENTRY_BLOCKS_ROLL_SEC - 10
    assert eng._roll_entry_blocks_if_stale() is True
    assert eng._entry_blocks == {}
    assert eng._entry_blocks_cum["X"]["primary"]["signals"]["spread"] == 1

    eng._tally_entry("X", "spread", bar_key=("m15", 2))
    eng.reset_entry_blocks()
    assert eng._entry_blocks == {}
    assert eng._entry_blocks_cum["X"]["primary"]["signals"]["spread"] == 2


def test_forget_leaves_cumulative():
    eng = _bare_engine()
    eng._tally_entry("X", "seans_disi", bar_key=("m30", 9))
    eng.forget_entry_blocks("X")
    assert "X" not in eng._entry_blocks
    assert eng._entry_blocks_cum["X"]["primary"]["signals"]["seans_disi"] == 1


def test_flush_persists_cumulative(store=None):
    store = _Store()
    eng = _bare_engine(store)
    eng._tally_entry("X", "spread", bar_key=("m15", 3))
    eng._flush_entry_blocks(force=True)
    assert "entry_blocks_cumulative" in store.saved
    assert store.saved["entry_blocks_cumulative"]["X"]["primary"]["signals"]["spread"] == 1
    assert store.saved.get("entry_blocks_cumulative_since") == eng._entry_blocks_cum_since


def test_entry_blocks_payload_includes_cumulative():
    eng = _bare_engine()
    eng._tally_entry("X", "spread", bar_key=("m15", 4))
    data = eng.entry_blocks()
    assert "cumulative" in data
    assert data["cumulative"]["signals"] >= 1
    assert data["cumulative"]["rows"]
