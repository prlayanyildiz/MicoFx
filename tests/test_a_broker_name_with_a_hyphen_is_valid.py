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



from micofx.models import is_valid_instrument_name


def _accepts(name: str) -> bool:
    """Ask the real rule, not a re-implementation of it.

    This used to grep store.py for the line containing ``ch.isalnum() or ch in``
    and re-derive the allowed characters from it with a regex. That made the
    file fail on 05.09 for a change that did not alter the rule at all: the rule
    moved into ``models.is_valid_instrument_name`` so the web layer's
    broker_symbol patch could share it instead of keeping a second copy - which
    is exactly what ``test_add_symbol_is_the_only_place_that_checks`` below
    asks for. A test that reads the source cannot tell "the rule changed" from
    "the rule moved", and it re-implements the very logic it is checking.

    ``add_symbol`` upper-cases and turns spaces into underscores before the
    check, so that normalisation is applied here too.
    """
    cleaned = str(name or "").strip().upper().replace(" ", "_")
    return is_valid_instrument_name(cleaned)


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


def test_there_is_still_exactly_one_copy_of_this_rule():
    """A second copy of this rule is how the two doors drift apart.

    Two doors need it now: ``Store.add_symbol`` for a new row, and the web
    layer's ``broker_symbol`` patch for repointing an existing one - the second
    was added 05.09, when broker_symbol turned out to have no validation at all.
    The answer is one shared function, not a second inline copy, so what this
    pins is that the character class is written down once.

    Named for what it checks rather than for store.py, which is no longer where
    it lives.
    """
    root = Path(__file__).resolve().parents[1] / "micofx"
    hits = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.py")
                  if "ch.isalnum() or ch in" in p.read_text(encoding="utf-8"))
    assert hits == ["models.py"], hits
