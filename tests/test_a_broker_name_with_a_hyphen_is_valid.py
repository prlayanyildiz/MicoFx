"""The broker names 158 tradeable instruments with a hyphen; we refused them.

Reported 15.08: adding ``BRENTOIL-PERP`` failed with "Gecerli bir sembol adi
yazin", which reads as though the operator mistyped. The symbol exists at the
broker and is tradeable (trade_mode 4). So does every dated equity CFD -
AAPL.US-24, XOM.US-24, and 156 others.

The check stays narrow past that. The name is used as a settings key, a dict
key and a URL path segment, so anything that would change what those mean -
slashes, spaces, quotes - is still refused.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.store import Store


class _Store:
    """Only the name check runs; the rest of add_symbol needs a real store."""

    symbols: dict = {}

    def _check(self, symbol: str) -> str:
        name = str(symbol or "").strip().upper().replace(" ", "_")
        if not name or not all(ch.isalnum() or ch in "._-" for ch in name):
            raise ValueError("bad")
        return name


def _accepts(name: str) -> bool:
    import re

    src = Path(__file__).resolve().parents[1] / "micofx" / "store.py"
    line = [ln for ln in src.read_text(encoding="utf-8").splitlines()
            if "ch.isalnum() or ch in" in ln][0]
    allowed = re.search(r'ch in "([^"]*)"', line).group(1)
    cleaned = str(name).strip().upper().replace(" ", "_")
    return bool(cleaned) and all(c.isalnum() or c in allowed for c in cleaned)


@pytest.mark.parametrize("name", ["BRENTOIL-PERP", "AAPL.US-24", "XOM.US-24",
                                  "BTC-PERP", "US500"])
def test_real_broker_names_are_accepted(name):
    assert _accepts(name), f"{name} exists at the broker and was refused"


@pytest.mark.parametrize("name", ["", "   ", "A/B", "A B C!", "DROP TABLE;",
                                  "a\b", "x?y", "p#q"])
def test_names_that_would_change_a_key_or_a_path_are_still_refused(name):
    assert not _accepts(name), f"{name!r} should not be a symbol name"


def test_a_space_still_becomes_an_underscore():
    assert _accepts("SPOT BRENT")


def test_the_message_names_the_hyphen():
    src = (Path(__file__).resolve().parents[1] / "micofx" / "store.py").read_text(
        encoding="utf-8")
    i = src.index("Gecerli bir sembol adi yazin")
    assert "-" in src[i:i + 80], "the error should say what is allowed"


def test_add_symbol_is_the_only_place_that_checks():
    """A second copy of this rule is how the two doors drift apart."""
    root = Path(__file__).resolve().parents[1] / "micofx"
    hits = [p.name for p in root.rglob("*.py")
            if "ch.isalnum() or ch in" in p.read_text(encoding="utf-8")]
    assert hits == ["store.py"], hits
