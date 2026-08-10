"""H1: soft-seed (POST /api/symbols-seed?overwrite=false -> Store.seed_symbols)
writes each defaults.json entry's *fixed* magic verbatim. If that magic was
since handed to a custom symbol (its default sibling deleted, next_magic()
recycled the number), or is still owned by a pending secondary_orphan_scan
window or a live orphan ticket, writing it back collides - engine.py's
by_magic lookup is last-write-wins, so two symbols end up sharing a magic
(wrong trail/BE), and a scan watching that magic would force-close a fresh
fill on the new symbol as a "delayed orphan ticket".
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import store as store_module
from micofx.store import Store


def _fresh_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    return Store()


def _victim(store) -> tuple[str, int]:
    """A shipped symbol to delete, and the magic that frees up.

    These tests used to name AUDUSD and the literal 990101, because that pair
    happened to sit exactly on next_magic()'s starting number. Removing AUDUSD
    from the portfolio broke six tests that were about magic reuse and not
    about AUDUSD at all. Picking the victim from whatever defaults.json
    actually ships keeps them pinned to the behaviour instead of to the
    roster.
    """
    symbol = min(store.symbols, key=lambda s: store.symbols[s].magic)
    return symbol, store.symbols[symbol].magic


def _take_magic(store, name: str, magic: int):
    """Create a custom symbol holding ``magic`` exactly.

    The old tests relied on next_magic() handing this number out by itself,
    which only worked while the freed magic was the lowest one it would
    reach. Claiming it explicitly states the precondition the test needs.
    """
    store.add_symbol(name, group="forex")
    return store.update_symbol(name, {"magic": magic})


def test_soft_seed_avoids_magic_taken_by_custom_symbol(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    victim, magic = _victim(s)
    s.delete_symbol(victim)
    custom = _take_magic(s, "MYPAIR", magic)
    assert custom.magic == magic

    seeded = s.seed_symbols(overwrite=False)

    assert seeded >= 1
    assert victim in s.symbols
    assert s.symbols[victim].magic != magic
    magics = [c.magic for c in s.symbols.values()]
    assert len(magics) == len(set(magics))  # no duplicate magics anywhere


def test_soft_seed_avoids_magic_held_by_pending_orphan_scan(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    victim, magic = _victim(s)
    s.delete_symbol(victim)
    # A pending secondary_orphan_scan is watching that magic even though no
    # symbol in the portfolio currently owns it (e.g. the scan outlived its
    # own symbol's deletion).
    s.set_setting("secondary_orphan_scan",
                  {"SOMESYM": {"magic": magic, "known": [], "since": 0.0}})

    s.seed_symbols(overwrite=False)

    assert s.symbols[victim].magic != magic


def test_soft_seed_does_not_overwrite_existing_symbol(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    victim, _ = _victim(s)
    s.update_symbol(victim, {"sl_atr_mult": 9.99})

    s.seed_symbols(overwrite=False)

    assert s.symbols[victim].sl_atr_mult == 9.99


def test_soft_seed_passes_through_avoid_magics(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    victim, magic = _victim(s)
    s.delete_symbol(victim)

    # Simulates a live orphan-ticket magic the web layer resolved via
    # client.positions() (Store itself has no client access for that half).
    s.seed_symbols(overwrite=False, avoid_magics={magic})

    assert s.symbols[victim].magic != magic


def test_reset_recreate_avoids_magic_taken_by_custom_symbol(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    victim, magic = _victim(s)
    s.delete_symbol(victim)
    custom = _take_magic(s, "MYPAIR", magic)
    assert custom.magic == magic

    updated = s.reset_symbol_to_preset(victim)

    assert updated is not None
    assert updated.magic != magic
    magics = [c.magic for c in s.symbols.values()]
    assert len(magics) == len(set(magics))


def test_reset_recreate_avoids_magic_held_by_orphan_scan(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    victim, magic = _victim(s)
    s.delete_symbol(victim)
    s.set_setting("secondary_orphan_scan",
                  {"SOMESYM": {"magic": magic, "known": [], "since": 0.0}})

    updated = s.reset_symbol_to_preset(victim)

    assert updated is not None
    assert updated.magic != magic
