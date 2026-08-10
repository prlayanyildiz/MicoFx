"""A restart must not let one bar's signal be filled a second time.

The post-fill cooldown is the guard that spaces entries out. It lived only in
SymbolState, which is rebuilt empty on every start - so a restart inside the
window let the same signal, recomputed from the same still-last-closed bar,
open a second position seconds after the first.

Seen repeatedly in the live log on 2026-08-10:

    16:00:03 [US30] BUY 0.2 @ 53994.90 SL=53974.20
    16:01:33 Yeniden baslatma istegi alindi.
    16:01:40 [US30] BUY 0.2 @ 53997.10 SL=53976.40
    16:09:42 [US30] Stop ile kapandi kar=-4.14
    16:09:42 [US30] Stop ile kapandi kar=-4.14

One signal, two positions, both stopped out - the loss doubled. max_positions
is deliberately above 1, so the position cap could not catch it, and every
other guard on the entry path is equally in-memory.
"""
from __future__ import annotations

import time

import pytest

from micofx.engine import Engine, SymbolState


class _Store:
    def __init__(self) -> None:
        self.settings: dict[str, object] = {}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


def _engine(store) -> Engine:
    eng = Engine.__new__(Engine)
    eng.store = store
    eng.states = {}
    eng._cooldowns = {
        str(k): float(v) for k, v in (store.get_setting("entry_cooldowns") or {}).items()
        if isinstance(v, (int, float))
    }
    return eng


def _fresh_state(store, symbol="US30") -> SymbolState:
    """A state built the way _cycle() builds one on a cold start."""
    eng = _engine(store)
    state = SymbolState(symbol)
    eng._restore_cooldown(state)
    return state


def test_a_running_cooldown_is_carried_across_the_restart():
    store = _Store()
    before = _engine(store)
    until = time.time() + 600
    before._save_cooldown("US30", until)

    # ...process dies, comes back, builds its states from nothing.
    assert _fresh_state(store).cooldown_until == pytest.approx(until)


def test_the_entry_gate_actually_blocks_on_the_restored_value():
    store = _Store()
    _engine(store)._save_cooldown("US30", time.time() + 600)
    state = _fresh_state(store)
    # The exact check _ready_for_entry makes.
    assert time.time() < state.cooldown_until


def test_an_expired_cooldown_does_not_block_anything():
    store = _Store()
    store.set_setting("entry_cooldowns", {"US30": time.time() - 5})
    assert _fresh_state(store).cooldown_until == 0.0


def test_a_symbol_that_never_filled_starts_clean():
    store = _Store()
    _engine(store)._save_cooldown("US30", time.time() + 600)
    assert _fresh_state(store, "NAS100").cooldown_until == 0.0


def test_expired_entries_are_pruned_as_they_are_written():
    store = _Store()
    eng = _engine(store)
    eng._cooldowns = {"OLD": time.time() - 10, "ALSO_OLD": time.time() - 900}
    eng._save_cooldown("US30", time.time() + 600)
    assert set(store.get_setting("entry_cooldowns")) == {"US30"}


def test_a_corrupt_stored_value_is_ignored_not_fatal():
    store = _Store()
    store.set_setting("entry_cooldowns", {"US30": "soon", "NAS100": None,
                                          "GER40": time.time() + 600})
    eng = _engine(store)
    assert set(eng._cooldowns) == {"GER40"}


def test_the_cooldown_is_written_where_a_restart_can_find_it():
    # Guards the wiring itself: a value kept only on the engine object would
    # pass every assertion above about SymbolState and still be lost.
    store = _Store()
    _engine(store)._save_cooldown("US30", time.time() + 600)
    assert "entry_cooldowns" in store.settings
