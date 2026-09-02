"""Lifetime entry_blocks counters must not feed auto-pilot forever.

``_flush_entry_blocks`` only debounces SQLite writes (45s). Counters used to
accumulate from first load with no age window, so income_dev_loop acted on
17-day spread tallies. Roll the counter blob (not the bounded events ring)
when ``entry_blocks_since`` is older than the window.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import ENTRY_BLOCKS_ROLL_SEC, Engine


class _Store:
    def __init__(self):
        self.saved = {}
        self.symbols = {"GER40": object()}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)

    def set_setting(self, key, value):
        self.saved[key] = value


def _engine(store=None, since=None):
    eng = object.__new__(Engine)
    eng.store = store or _Store()
    eng._entry_blocks = {
        "GER40": {"primary": {"attempts": {"spread": 9}, "signals": {"spread": 3}}},
    }
    eng._entry_last_bar = {"GER40": {"primary": ("x", "spread")}}
    eng._entry_events = [{"symbol": "GER40", "reason": "spread", "epoch": 1}]
    eng._entry_blocks_since = float(since if since is not None else time.time())
    eng._entry_blocks_dirty = False
    eng._entry_events_dirty = False
    eng._entry_blocks_flushed_at = 0.0
    return eng


def test_stale_counters_roll_on_flush_and_keep_events():
    store = _Store()
    old = time.time() - ENTRY_BLOCKS_ROLL_SEC - 10
    eng = _engine(store, since=old)
    eng._entry_blocks_dirty = True
    eng._flush_entry_blocks(force=True)
    assert eng._entry_blocks == {}
    assert eng._entry_last_bar == {}
    assert eng._entry_events  # ring kept
    assert eng._entry_blocks_since > old
    assert store.saved["entry_blocks"] == {}
    assert store.saved["entry_blocks_since"] == eng._entry_blocks_since


def test_fresh_counters_are_not_wiped():
    eng = _engine(since=time.time())
    eng._entry_blocks_dirty = True
    before = dict(eng._entry_blocks)
    eng._flush_entry_blocks(force=True)
    assert eng._entry_blocks == before
