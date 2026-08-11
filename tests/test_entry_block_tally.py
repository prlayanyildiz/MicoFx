"""Why entries do not happen, counted - the one thing a running bot never recorded.

Every symbol in this book trades far under the frequency its own holdout
implies (7-38%). _try_entry sets state.note and returns; the note is
overwritten next cycle, nothing is logged and nothing is counted, so from a
running system the shortfall was unattributable.

Two counts, because the first one alone misleads. A blocked signal is
re-offered every poll until its bar rolls over, so on a 2s interval one
refused signal shows up as hundreds of attempts - EURJPY produced 339 from a
single sell in thirteen minutes. ``attempts`` therefore measures how long the
gate held a signal off; ``signals`` counts distinct (bar, reason) episodes and
is the one that compares to a holdout trade count.

Legs are counted separately because the ensemble's second leg carries its own
parameters, and it is routinely the tighter one - six of thirteen live symbols
have a secondary spread ceiling below their primary, up to 3.6x on EURJPY
(0.18 primary, 0.05 secondary). _try_entry gates whichever leg produced the
signal, so a tally that merged them would report a symbol as blocked without
saying which config owns the ceiling doing it.

Read together they separate the two causes that look the same from outside:

  * signals near the holdout's implied count, few opened
      -> a gate is eating them, and ``blocks`` names which
  * signals themselves short
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
    """Real Store always exposes .symbols; the flush prunes against it."""

    def __init__(self, symbols=None):
        self.saved = {}
        self.symbols = {s: object() for s in
                        (symbols if symbols is not None else
                         ("X", "A", "B", "AYNI", "EURJPY", "UK100", "GER40",
                          "FRA40", "GBPUSD", "NAS100", "BUSY", "QUIET",
                          "KALAN", "US500", "US30"))}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)

    def set_setting(self, key, value):
        self.saved[key] = value


def _engine(store=None):
    eng = object.__new__(Engine)
    eng.store = store or _Store()
    eng._entry_blocks = {}
    eng._entry_last_bar = {}
    eng._entry_blocks_since = 1000.0
    eng._entry_blocks_dirty = False
    return eng


def _row(eng, symbol, leg="primary"):
    return next(r for r in eng.entry_blocks()["rows"]
                if r["symbol"] == symbol and r["leg"] == leg)


# ------------------------------------------------------------ the counter

def test_a_refusal_is_counted_against_its_own_gate():
    eng = _engine()
    eng._tally_entry("UK100", "spread", bar_key=(1, 0))
    eng._tally_entry("UK100", "acildi", bar_key=(2, 0))
    row = _row(eng, "UK100")
    assert row["signals"] == 2
    assert row["opened"] == 1
    assert row["fill_rate"] == 0.5
    assert row["blocks"] == {"spread": 1}


def test_a_retried_signal_counts_once_however_many_polls_it_takes():
    """The whole point: one refused EURJPY sell produced 339 attempts."""
    eng = _engine()
    for _ in range(339):
        eng._tally_entry("EURJPY", "spread", bar_key=(7, 0), source="secondary")
    row = _row(eng, "EURJPY", "secondary")
    assert row["signals"] == 1, "tekrar denemeler sinyal sayisini sisirdi"
    assert row["attempts"] == 339
    assert row["blocks"] == {"spread": 1}
    assert row["retries"] == {"spread": 339}


def test_a_new_bar_starts_a_new_episode():
    eng = _engine()
    for bar in (1, 2, 3):
        for _ in range(50):
            eng._tally_entry("X", "spread", bar_key=(bar, 0))
    row = _row(eng, "X")
    assert row["signals"] == 3
    assert row["attempts"] == 150


def test_a_new_reason_on_the_same_bar_is_its_own_episode():
    """The gate that refuses can change mid-bar as the spread moves."""
    eng = _engine()
    eng._tally_entry("X", "spread", bar_key=(1, 0))
    eng._tally_entry("X", "risk_limiti", bar_key=(1, 0))
    row = _row(eng, "X")
    assert row["blocks"] == {"spread": 1, "risk_limiti": 1}


def test_the_two_legs_are_counted_separately():
    """Six of thirteen symbols carry a tighter ceiling on the secondary."""
    eng = _engine()
    eng._tally_entry("EURJPY", "acildi", bar_key=(1, 0), source="primary")
    eng._tally_entry("EURJPY", "spread", bar_key=(1, 0), source="secondary")
    assert _row(eng, "EURJPY", "primary")["opened"] == 1
    assert _row(eng, "EURJPY", "secondary")["blocks"] == {"spread": 1}


def test_opened_is_not_listed_as_a_block():
    eng = _engine()
    eng._tally_entry("X", "acildi", bar_key=(1, 0))
    row = _row(eng, "X")
    assert "acildi" not in row["blocks"]
    assert row["opened"] == 1


def test_an_unmarked_return_is_bucketed_rather_than_lost():
    eng = _engine()
    eng._tally_entry("X", "", bar_key=(1, 0))
    eng._tally_entry("X", None, bar_key=(2, 0))
    assert _row(eng, "X")["blocks"] == {"isaretsiz": 2}


def test_totals_add_up_across_symbols():
    eng = _engine()
    for bar in (1, 2, 3):
        eng._tally_entry("A", "spread", bar_key=(bar, 0))
    eng._tally_entry("B", "spread", bar_key=(1, 0))
    eng._tally_entry("B", "risk_limiti", bar_key=(1, 0))
    data = eng.entry_blocks()
    assert data["totals"] == {"spread": 4, "risk_limiti": 1}
    assert data["signals"] == 5
    assert data["opened"] == 0


def test_the_busiest_symbol_sorts_first():
    eng = _engine()
    eng._tally_entry("QUIET", "spread", bar_key=(1, 0))
    for bar in range(5):
        eng._tally_entry("BUSY", "spread", bar_key=(bar, 0))
    assert eng.entry_blocks()["rows"][0]["symbol"] == "BUSY"


# --------------------------------------------------------- persistence

def test_the_tally_survives_a_restart():
    store = _Store()
    eng = _engine(store)
    eng._tally_entry("X", "spread", bar_key=(1, 0))
    eng._flush_entry_blocks()
    assert store.saved["entry_blocks"]["X"]["primary"]["signals"] == {"spread": 1}

    revived = _engine(store)
    revived._entry_blocks = {
        sym: {leg: {f: {str(k): int(v) for k, v in c.get(f, {}).items()}
                    for f in ("attempts", "signals")}
              for leg, c in legs.items()}
        for sym, legs in store.get_setting("entry_blocks", {}).items()
    }
    assert revived.entry_blocks()["totals"] == {"spread": 1}


def test_a_flat_legacy_payload_is_dropped_not_coerced():
    """The shape this shipped with for one afternoon. Half-read is worse
    than empty, because it looks like evidence."""
    store = _Store()
    store.saved["entry_blocks"] = {"X": {"spread": 12}}
    eng = _engine(store)
    restored = {}
    for sym, legs in store.get_setting("entry_blocks", {}).items():
        if not isinstance(legs, dict):
            continue
        kept = {}
        for leg, counts in legs.items():
            if not isinstance(counts, dict):
                continue
            buckets = {}
            for field in ("attempts", "signals"):
                raw = counts.get(field)
                if not isinstance(raw, dict):
                    break
                buckets[field] = {str(k): int(v) for k, v in raw.items()}
            else:
                kept[str(leg)] = buckets
        if kept:
            restored[str(sym)] = kept
    eng._entry_blocks = restored
    assert eng.entry_blocks()["rows"] == []


def test_a_clean_cycle_writes_nothing():
    store = _Store()
    eng = _engine(store)
    eng._flush_entry_blocks()
    assert store.saved == {}


def test_a_reset_starts_a_fresh_window():
    store = _Store()
    eng = _engine(store)
    eng._tally_entry("X", "spread", bar_key=(1, 0))
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
    eng._tally_entry("X", "spread", bar_key=(1, 0))
    eng._flush_entry_blocks()
    assert eng.entry_blocks()["totals"] == {"spread": 1}


def test_a_hostile_symbol_key_does_not_raise():
    eng = _engine()
    eng._tally_entry(None, "spread", bar_key=(1, 0))
    eng._tally_entry(12345, "spread", bar_key=(1, 0))
    assert eng.entry_blocks()["signals"] == 2


def test_an_unhashable_bar_key_does_not_raise():
    eng = _engine()
    eng._tally_entry("X", "spread", bar_key=["not", "a", "tuple"])
    assert eng.entry_blocks()["signals"] == 1


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
