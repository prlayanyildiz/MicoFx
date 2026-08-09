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


def test_soft_seed_avoids_magic_taken_by_custom_symbol(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    # AUDUSD ships with magic 990101 in defaults.json - delete it, then have
    # a custom symbol claim that exact magic via next_magic()'s natural
    # sequence, then soft-seed AUDUSD back in.
    s.delete_symbol("AUDUSD")
    custom = s.add_symbol("MYPAIR", group="forex")
    assert custom.magic == 990101

    seeded = s.seed_symbols(overwrite=False)

    assert seeded >= 1
    assert "AUDUSD" in s.symbols
    audusd_magic = s.symbols["AUDUSD"].magic
    assert audusd_magic != 990101
    magics = [c.magic for c in s.symbols.values()]
    assert len(magics) == len(set(magics))  # no duplicate magics anywhere


def test_soft_seed_avoids_magic_held_by_pending_orphan_scan(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    s.delete_symbol("AUDUSD")
    # A pending secondary_orphan_scan is watching 990101 even though no
    # symbol in the portfolio currently owns it (e.g. the scan outlived its
    # own symbol's deletion).
    s.set_setting("secondary_orphan_scan", {"SOMESYM": {"magic": 990101, "known": [], "since": 0.0}})

    s.seed_symbols(overwrite=False)

    assert s.symbols["AUDUSD"].magic != 990101


def test_soft_seed_does_not_overwrite_existing_symbol(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    s.update_symbol("AUDUSD", {"sl_atr_mult": 9.99})

    s.seed_symbols(overwrite=False)

    assert s.symbols["AUDUSD"].sl_atr_mult == 9.99


def test_soft_seed_passes_through_avoid_magics(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    s.delete_symbol("AUDUSD")

    # Simulates a live orphan-ticket magic the web layer resolved via
    # client.positions() (Store itself has no client access for that half).
    s.seed_symbols(overwrite=False, avoid_magics={990101})

    assert s.symbols["AUDUSD"].magic != 990101


def test_reset_recreate_avoids_magic_taken_by_custom_symbol(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    s.delete_symbol("AUDUSD")
    custom = s.add_symbol("MYPAIR", group="forex")
    assert custom.magic == 990101

    updated = s.reset_symbol_to_preset("AUDUSD")

    assert updated is not None
    assert updated.magic != 990101
    magics = [c.magic for c in s.symbols.values()]
    assert len(magics) == len(set(magics))


def test_reset_recreate_avoids_magic_held_by_orphan_scan(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    s.delete_symbol("AUDUSD")
    s.set_setting("secondary_orphan_scan",
                  {"SOMESYM": {"magic": 990101, "known": [], "since": 0.0}})

    updated = s.reset_symbol_to_preset("AUDUSD")

    assert updated is not None
    assert updated.magic != 990101
