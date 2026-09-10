"""The traded book is one list, however many files write it out.

``config/defaults.json`` is the shipped book. Two ops scripts under
``scripts/`` also carry a ``BOOK`` tuple, and both still named the seven-symbol
portfolio after JPN225 and BTCUSD were deleted on 10.09 - so every audit they
printed described two names the live book no longer has, and every "aktif
semboller" line they emitted was wrong by two.

Same reason the scripts keep their own ``PANEL`` literal rather than importing
one (see test_one_address_one_interpreter): these are single-file, stdlib-only
tools meant to be run by path, and ``micofx`` is not importable that way. So
the copies stay and this file makes them unable to disagree with the shipped
list.

Deleting a symbol is a book change and must trip this. That is the point: it
should not be possible to cut a name from the panel and leave four other files
still counting it.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.paths import DEFAULTS_PATH

ROOT = Path(__file__).resolve().parents[1]

# Scripts that hardcode the book. Listed, not globbed: a new one should be
# added here deliberately, or it will drift unnoticed exactly as these did.
BOOK_SCRIPTS = ("scripts/income_dev_loop.py", "scripts/unfreeze_prep.py")


def shipped_book() -> tuple[str, ...]:
    cfg = json.loads(DEFAULTS_PATH.read_text(encoding="utf-8-sig"))
    return tuple(str(e["symbol"]) for e in cfg["symbols"])


def _book_literal(rel: str) -> tuple[str, ...]:
    """The ``BOOK = (...)`` tuple, read as source rather than imported.

    Importing would run the module, and these scripts open sockets to the
    panel at import time.
    """
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "BOOK":
                return tuple(ast.literal_eval(node.value))
    raise AssertionError(f"{rel}: BOOK bulunamadi - adi mi degisti?")


def test_the_shipped_book_is_what_the_operator_left():
    assert set(shipped_book()) == {"GER40", "NAS100", "US30", "XAUUSD"}, (
        f"kitap degisti: {shipped_book()}")


def test_every_script_book_matches_the_shipped_one():
    want = set(shipped_book())
    for rel in BOOK_SCRIPTS:
        got = set(_book_literal(rel))
        assert got == want, (
            f"{rel} kitabi gonderilen listeyle uyusmuyor: "
            f"fazla={sorted(got - want)} eksik={sorted(want - got)}")


def test_no_script_book_names_a_retired_symbol():
    """Belt and braces: the shipped list is guarded against RETIRED_SYMBOLS by
    test_bilingual_stale_retired_scan, so matching it already implies this.
    Stated separately because the two lists could both be edited at once."""
    from tests.retired_lexicon import RETIRED_SYMBOLS

    for rel in BOOK_SCRIPTS:
        for name in _book_literal(rel):
            assert name not in RETIRED_SYMBOLS, f"{rel} emekli sembol tasiyor: {name}"
