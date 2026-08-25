"""Entry-block events: persist the bar identity the counters throw away.

G7 could not score blocked bars because ``entry_blocks`` kept counts and
``_entry_last_bar`` lived only in memory. These tests pin a ring of
(symbol, reason, bar_key, epoch) that is observation-only: it must not
replace the counters, and it must not be read by the entry path.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import ENTRY_EVENT_LIMIT, Engine


class _Store:
    def __init__(self):
        self.saved = {}
        self.symbols = {"X": object(), "GER40": object(), "UK100": object()}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)

    def set_setting(self, key, value):
        self.saved[key] = value


def _engine(store=None):
    eng = object.__new__(Engine)
    eng.store = store or _Store()
    eng._entry_blocks = {}
    eng._entry_last_bar = {}
    eng._entry_events = []
    eng._entry_blocks_since = 1000.0
    eng._entry_blocks_dirty = False
    eng._entry_events_dirty = False
    eng._entry_blocks_flushed_at = 0.0
    return eng


def test_a_new_signal_episode_records_the_bar():
    eng = _engine()
    eng._tally_entry("GER40", "spread", bar_key=("primary", 1_786_698_530))
    assert len(eng._entry_events) == 1
    ev = eng._entry_events[0]
    assert ev["symbol"] == "GER40"
    assert ev["reason"] == "spread"
    assert ev["bar_key"] == ["primary", 1786698530]
    assert ev["epoch"] > 0


def test_retries_on_the_same_bar_do_not_grow_the_ring():
    eng = _engine()
    for _ in range(50):
        eng._tally_entry("UK100", "ai_gate", bar_key=(7, 0))
    assert len(eng._entry_events) == 1


def test_the_ring_keeps_the_newest_n():
    eng = _engine()
    eng._entry_event_limit = 3
    for bar in range(5):
        eng._tally_entry("X", "spread", bar_key=(bar, 0))
    assert [e["bar_key"][0] for e in eng._entry_events] == [2, 3, 4]


def test_events_survive_a_restart():
    store = _Store()
    eng = _engine(store)
    eng._tally_entry("X", "spread", bar_key=(1, 0))
    eng._flush_entry_blocks()
    assert "entry_block_events" in store.saved
    assert store.saved["entry_blocks"]["X"]["primary"]["signals"] == {"spread": 1}

    revived = _engine(store)
    revived._load_entry_events()
    assert len(revived._entry_events) == 1
    assert revived._entry_events[0]["symbol"] == "X"
    assert revived._entry_events[0]["reason"] == "spread"
    assert revived._entry_events[0]["bar_key"] == [1, 0]


def test_the_limit_covers_a_few_weeks_at_the_measured_rate():
    """14-16.08 produced 156 signals in 2 days -> 78/day. 2048 ~= 26 days."""
    assert ENTRY_EVENT_LIMIT == 2048
    assert ENTRY_EVENT_LIMIT / 78 > 14


def test_counters_are_not_replaced_by_the_ring():
    eng = _engine()
    eng._tally_entry("X", "spread", bar_key=(1, 0))
    eng._tally_entry("X", "spread", bar_key=(1, 0))
    data = eng.entry_blocks()
    assert data["signals"] == 1
    assert data["totals"] == {"spread": 1}


def test_evaluate_needles_the_two_silent_halts():
    """Those two gates return before _try_entry, so the ready-loop tally never
    sees them. Silence in the panel is not evidence they never fire."""
    src = Path("micofx/engine.py").read_text(encoding="utf-8")
    cycle = src.split("def _cycle(", 1)[1].split("\n    def ", 1)[0]
    assert "gunluk_halt" in cycle
    eval_body = src.split("def _evaluate(", 1)[1].split("\n    def ", 1)[0]
    assert "sembol_halt" in eval_body
    assert "_tally_entry" in eval_body
    # Daily halt means allow_entry is False and ready stays empty. The flush
    # used to live inside that `if`, so halt tallies never reached the store.
    # Cycle-body indent is 8 spaces; the ready-block is 12.
    assert any(line.startswith("        self._flush_entry_blocks()")
               for line in cycle.splitlines()), (
        "halt tallies never persist when ready is empty")


def test_a_retry_does_not_rewrite_the_events_blob():
    """The 222 KB ring must not hit disk on every 2s poll.

    Counters used to (1.3 KB). They now wait 45s unless a new episode
    marks the ring dirty, which is the write that must still be immediate.
    """
    store = _Store()
    writes: list[str] = []
    orig = store.set_setting

    def tracking(key, value):
        writes.append(key)
        orig(key, value)

    store.set_setting = tracking
    eng = _engine(store)
    eng._tally_entry("X", "spread", bar_key=(1, 0))
    eng._flush_entry_blocks()
    assert writes.count("entry_block_events") == 1
    assert "entry_blocks" in writes

    writes.clear()
    eng._tally_entry("X", "spread", bar_key=(1, 0))
    eng._flush_entry_blocks()
    assert "entry_block_events" not in writes, "retry rewrote the events blob"
    assert "entry_blocks" not in writes, "counter retries must wait the debounce"

    writes.clear()
    eng._tally_entry("X", "spread", bar_key=(2, 0))
    eng._flush_entry_blocks()
    assert writes.count("entry_block_events") == 1


def test_the_entry_path_does_not_read_the_event_ring():
    src = Path("micofx/engine.py").read_text(encoding="utf-8")
    try_entry = src.split("def _try_entry(", 1)[1].split("\n    def ", 1)[0]
    assert "_entry_events" not in try_entry
    assert "entry_block_events" not in try_entry
