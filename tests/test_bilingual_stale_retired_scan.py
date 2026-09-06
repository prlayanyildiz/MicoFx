"""Stale / retired / dead-code scans with Turkish + English vocabulary.

Same retired names and gone-words as ``test_docs_match_the_code``; this file
extends coverage to shipped config and panel strings an agent might edit
without opening README.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import STRATEGIES, TIMEFRAMES
from tests.retired_lexicon import (
    GONE_WORDS,
    RETIRED_FAMILIES,
    RETIRED_SYMBOLS,
    RETIRED_TIMEFRAMES,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "config" / "defaults.json"
PANEL_FILES = (
    ROOT / "micofx" / "web" / "static" / "app.js",
    ROOT / "micofx" / "web" / "static" / "field_help.js",
)
# docs/KULLANIM.md joined 05.09. Until then ``docs/`` was scanned by no guard
# at all, and it had gone the furthest out of date of anything in the repo: it
# still advertised a 10-symbol portfolio naming four retired symbols, omitted
# BTCUSD entirely, and offered "M5/M15/M30/H1" as the searchable bars. It is
# the file an operator actually reads, so it is now guarded like the rest.
DOC_FILES = ("README.md", "MASTER_PROMPT.md", "AGENTS.md", "docs/KULLANIM.md")


def _says_removed(lines: list[str], i: int) -> bool:
    window = " ".join(lines[max(0, i - 2): i + 3]).lower()
    return any(w in window for w in GONE_WORDS)


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_shipped_defaults_only_list_live_families():
    data = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    opt = data["optimizer"]
    # ``<=``, not ``==``: the shipped list is the *searched* subset, and a
    # dormant family (sweep_fade / range_fade) is in STRATEGIES without being
    # offered to the optimizer. Equality here would fail red until someone
    # "fixed" it by adding the dormant names to defaults.json - which is the
    # accidental-activation path this file exists to close.
    assert set(opt["strategies"]) <= set(STRATEGIES)
    assert set(opt["strategy_grids"]) <= set(STRATEGIES)
    assert set(opt["timeframes"]) <= set(TIMEFRAMES)


def test_shipped_starter_book_names_no_retired_symbol():
    """``overwrite=true`` seeding DELETES the portfolio and rebuilds it from
    this list, so a stale entry here is a live-book risk, not a doc typo.
    """
    book = json.loads(DEFAULTS.read_text(encoding="utf-8"))["symbols"]
    names = [str(e.get("symbol") or "") for e in book]
    assert names, "defaults.json ships an empty starter book"
    for retired in RETIRED_SYMBOLS:
        assert retired not in names, (
            f"defaults.json still seeds retired symbol {retired!r}; "
            f"'varsayilana don' would rebuild the old portfolio")
    magics = [e.get("magic") for e in book]
    assert len(set(magics)) == len(magics), f"duplicate seed magic: {magics}"
    assert len(set(names)) == len(names), f"duplicate seed symbol: {names}"


def test_panel_files_do_not_present_retired_families_as_live():
    for path in PANEL_FILES:
        lines = _read_lines(path)
        for i, line in enumerate(lines):
            if "(arsiv)" in line.lower():
                continue
            for fam in RETIRED_FAMILIES:
                if re.search(rf"\b{re.escape(fam)}\b", line) and not _says_removed(lines, i):
                    raise AssertionError(
                        f"{path.name}:{i + 1} emekli/retired '{fam}' canliymis gibi: "
                        f"{line[:80]}")


def test_docs_still_use_bilingual_gone_words_for_retired_families():
    for name in DOC_FILES:
        lines = _read_lines(ROOT / name)
        for i, line in enumerate(lines):
            for fam in RETIRED_FAMILIES:
                if re.search(rf"\b{re.escape(fam)}\b", line) and not _says_removed(lines, i):
                    raise AssertionError(
                        f"{name}:{i + 1} emekli aile '{fam}' canliymis gibi: "
                        f"{line[:70]}")


def test_retired_timeframes_are_not_offered_in_shipped_defaults():
    data = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    live = set(TIMEFRAMES)
    for tf in data["optimizer"]["timeframes"]:
        assert tf in live, f"defaults optimizer.timeframes names retired bar {tf!r}"


def test_retired_timeframe_names_in_docs_are_marked_gone():
    live = set(TIMEFRAMES)
    for name in DOC_FILES:
        lines = _read_lines(ROOT / name)
        for i, line in enumerate(lines):
            for tf in RETIRED_TIMEFRAMES:
                if tf in live:
                    continue
                if re.search(rf"\b{re.escape(tf)}\b", line) and not _says_removed(lines, i):
                    raise AssertionError(
                        f"{name}:{i + 1} emekli bar '{tf}' gone-word olmadan: {line[:70]}"
                    )
