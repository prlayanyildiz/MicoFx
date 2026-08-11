"""Why entries do not happen, counted - the one thing a running bot never recorded.

Every symbol in this book trades far under the frequency its own holdout
implies (7-38%). _try_entry sets state.note and returns; the note is
overwritten next cycle, nothing is logged and nothing is counted, so from a
running system the shortfall was unattributable.

The tally is taken only where a signal actually reached the entry stage -
_cycle skips a symbol with no signal - which is what makes it decisive. It
separates the two causes that look the same from outside:

  * attempts match the holdout's implied count, opened does not
      -> a gate is eating them, and ``blocks`` names which
  * attempts themselves are short
      -> the entry gates are innocent; signal generation is the problem
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine, SymbolState


class _Store:
    def __init__(self):
        self.saved = {}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)

    def set_setting(self, key, value):
        self.saved[key] = value


def _engine(store=None):
    eng = object.__new__(Engine)
    eng.store = store or _Store()
    eng._entry_blocks = {}
    eng._entry_blocks_since = 1000.0
    eng._entry_blocks_dirty = False
    return eng


# ------------------------------------------------------------ the counter

def test_a_refusal_is_counted_against_its_own_gate():
    eng = _engine()
    eng._tally_entry("UK100", "spread")
    eng._tally_entry("UK100", "spread")
    eng._tally_entry("UK100", "acildi")
    row = next(r for r in eng.entry_blocks()["rows"] if r["symbol"] == "UK100")
    assert row["attempts"] == 3
    assert row["opened"] == 1
    assert row["fill_rate"] == 0.333
    assert row["blocks"] == {"spread": 2}


def test_opened_is_not_listed_as_a_block():
    eng = _engine()
    eng._tally_entry("X", "acildi")
    row = eng.entry_blocks()["rows"][0]
    assert "acildi" not in row["blocks"]
    assert row["opened"] == 1


def test_an_unmarked_return_is_bucketed_rather_than_lost():
    """A future edit adding a return without a key must show up, not vanish."""
    eng = _engine()
    eng._tally_entry("X", "")
    eng._tally_entry("X", None)
    assert eng.entry_blocks()["rows"][0]["blocks"] == {"isaretsiz": 2}


def test_totals_add_up_across_symbols():
    eng = _engine()
    for _ in range(3):
        eng._tally_entry("A", "spread")
    eng._tally_entry("B", "spread")
    eng._tally_entry("B", "risk_limiti")
    data = eng.entry_blocks()
    assert data["totals"] == {"spread": 4, "risk_limiti": 1}
    assert data["attempts"] == 5
    assert data["opened"] == 0


def test_the_busiest_symbol_sorts_first():
    eng = _engine()
    eng._tally_entry("QUIET", "spread")
    for _ in range(5):
        eng._tally_entry("BUSY", "spread")
    assert [r["symbol"] for r in eng.entry_blocks()["rows"]] == ["BUSY", "QUIET"]


# --------------------------------------------------------- persistence

def test_the_tally_survives_a_restart():
    store = _Store()
    eng = _engine(store)
    eng._tally_entry("X", "spread")
    eng._flush_entry_blocks()
    assert store.saved["entry_blocks"] == {"X": {"spread": 1}}

    revived = _engine(store)
    revived._entry_blocks = {
        str(s): {str(k): int(v) for k, v in c.items()}
        for s, c in store.get_setting("entry_blocks", {}).items()
    }
    assert revived.entry_blocks()["totals"] == {"spread": 1}


def test_a_clean_cycle_writes_nothing():
    store = _Store()
    eng = _engine(store)
    eng._flush_entry_blocks()
    assert store.saved == {}


def test_a_reset_starts_a_fresh_window():
    store = _Store()
    eng = _engine(store)
    eng._tally_entry("X", "spread")
    eng._flush_entry_blocks()
    before = eng._entry_blocks_since
    eng.reset_entry_blocks()
    assert eng.entry_blocks()["rows"] == []
    assert eng._entry_blocks_since > before
    assert store.saved["entry_blocks"] == {}


# ------------------------------------------- diagnostics never break a cycle

def test_a_store_that_refuses_to_write_does_not_raise():
    class _Broken(_Store):
        def set_setting(self, key, value):
            raise RuntimeError("disk dolu")

    eng = _engine(_Broken())
    eng._tally_entry("X", "spread")
    eng._flush_entry_blocks()                 # must not raise
    assert eng.entry_blocks()["totals"] == {"spread": 1}


def test_a_hostile_symbol_key_does_not_raise():
    eng = _engine()
    eng._tally_entry(None, "spread")
    eng._tally_entry(12345, "spread")
    assert eng.entry_blocks()["attempts"] == 2


# ------------------------------------- every marked return has a live key

def test_every_rejection_in_try_entry_sets_a_key():
    """A `return` inside _try_entry with no entry_block leaves a blind spot."""
    src = (Path(__file__).resolve().parents[1] / "micofx" / "engine.py").read_text(
        encoding="utf-8")
    body = src.split("def _try_entry(", 1)[1]
    body = body.split("\n    def ", 1)[0]

    lines = body.splitlines()
    bare = []
    for i, line in enumerate(lines):
        if line.strip() != "return":
            continue
        # Walk back over the few lines that make up this exit and look for the
        # key. 6 lines covers every shape in there (note + signal clear + key).
        window = "\n".join(lines[max(0, i - 6):i])
        if "entry_block" not in window:
            bare.append(i)
    assert not bare, (
        f"_try_entry icinde entry_block'suz {len(bare)} return var - "
        f"satir(lar): {bare}")


def test_the_panel_is_wired_to_the_endpoint():
    """A renamed id leaves the view blank and nothing else notices."""
    web = Path(__file__).resolve().parents[1] / "micofx" / "web"
    js = (web / "static" / "app.js").read_text(encoding="utf-8")
    html = (web / "templates" / "index.html").read_text(encoding="utf-8")

    assert "/api/analysis/entry-blocks" in js
    for element_id in ("blocks-table", "blocks-note",
                       "btn-blocks-refresh", "btn-blocks-reset"):
        assert f'id="{element_id}"' in html, f"index.html'de {element_id} yok"
        assert f'"#{element_id}"' in js, f"app.js {element_id} kullanmiyor"
    assert "loadBlocks()" in js


def test_the_state_field_exists_and_starts_empty():
    st = SymbolState("X")
    assert st.entry_block == ""
    assert "entry_block" in SymbolState.__slots__
