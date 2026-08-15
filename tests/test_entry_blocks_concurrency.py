"""entry_blocks() runs on the web thread while the engine thread writes to it.

Nothing serialises the two. Engine._lock covers only start/stop/shutdown, so
every cross-thread read of engine state defends itself by snapshotting -
list(self.states.items()) at the two other sites. entry_blocks() did not, and
iterated the nested per-leg counters directly.

_tally_entry adds a NEW key to those inner dicts whenever the gate refusing a
symbol changes, which is ordinary operation rather than an edge case: a signal
goes from spread to risk_limiti to acildi as conditions move. A panel refresh
landing in that window raised "dictionary changed size during iteration" and
500'd the view.

Reproduced 3 times out of 3 with the fix reverted, and clean with it in place.
The failure is confined to the diagnostic endpoint - no trading path reads
this - but it is the view we are relying on to answer the frequency question,
so it going blank at the moment a gate changes is exactly the wrong time.

NOT reproduced, stated as such: json.dumps() inside store.set_setting()
iterates the same structure, and reset_entry_blocks() reaches it from the web
thread. Two seconds of hammering never tripped it, so no guard was added
there.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


class _Store:
    def __init__(self):
        self.saved = {}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)

    def set_setting(self, key, value):
        self.saved[key] = value


def _engine():
    eng = object.__new__(Engine)
    eng.store = _Store()
    eng._entry_blocks = {}
    eng._entry_last_bar = {}
    eng._entry_blocks_since = 1000.0
    eng._entry_blocks_dirty = False
    return eng


def _race(writer, reader, seconds=1.5):
    """Run writer and reader concurrently; return the first reader error."""
    eng = _engine()
    errors: list[Exception] = []
    stop = threading.Event()
    counter = {"i": 0}

    def write():
        while not stop.is_set():
            counter["i"] += 1
            writer(eng, counter["i"])

    def read():
        while not stop.is_set():
            try:
                reader(eng)
            except Exception as exc:      # noqa: BLE001 - that is the assertion
                errors.append(exc)
                return

    threads = [threading.Thread(target=write), threading.Thread(target=read)]
    for t in threads:
        t.start()
    time.sleep(seconds)
    stop.set()
    for t in threads:
        t.join(timeout=10)
    return errors


def test_a_new_block_reason_during_a_read_does_not_raise():
    """The reproducer: inner counter dicts growing mid-iteration."""
    errors = _race(
        lambda eng, i: eng._tally_entry("EURJPY", f"sebep{i}", bar_key=(i, 0)),
        lambda eng: eng.entry_blocks(),
    )
    assert not errors, f"{type(errors[0]).__name__}: {errors[0]}"


def test_a_new_symbol_during_a_read_does_not_raise():
    errors = _race(
        lambda eng, i: eng._tally_entry(f"S{i}", "spread", bar_key=(i, 0)),
        lambda eng: eng.entry_blocks(),
    )
    assert not errors, f"{type(errors[0]).__name__}: {errors[0]}"


def test_a_second_leg_appearing_during_a_read_does_not_raise():
    errors = _race(
        lambda eng, i: eng._tally_entry(
            "EURJPY", f"r{i % 3}", bar_key=(i, 0),
            source="secondary" if i % 2 else "primary"),
        lambda eng: eng.entry_blocks(),
    )
    assert not errors, f"{type(errors[0]).__name__}: {errors[0]}"


def test_a_reset_during_a_read_does_not_raise():
    """reset_entry_blocks() rebinds the dict from the web thread."""
    errors = _race(
        lambda eng, i: (eng._tally_entry("X", "spread", bar_key=(i, 0))
                        if i % 50 else eng.reset_entry_blocks()),
        lambda eng: eng.entry_blocks(),
    )
    assert not errors, f"{type(errors[0]).__name__}: {errors[0]}"


def test_the_snapshot_is_actually_taken():
    """Guards the fix itself - a later edit dropping list() reopens the race."""

    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "engine.py").read_text(encoding="utf-8")
    body = src.split("def entry_blocks(", 1)[1].split("\n    def ", 1)[0]
    for line in body.splitlines():
        stripped = line.strip()
        if ".items()" not in stripped or stripped.startswith("#"):
            continue
        # Every cross-thread iteration in here must go through list().
        if "self._entry_blocks" in stripped or "legs.items()" in stripped \
                or "counts.get(" in stripped:
            assert "list(" in stripped, f"anlik goruntu alinmamis: {stripped}"


def test_the_result_is_still_correct_under_no_contention():
    eng = _engine()
    eng._tally_entry("X", "spread", bar_key=(1, 0))
    eng._tally_entry("X", "acildi", bar_key=(2, 0))
    row = eng.entry_blocks()["rows"][0]
    assert row["signals"] == 2 and row["opened"] == 1
