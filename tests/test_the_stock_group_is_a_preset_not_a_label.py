""""stock" earns a group because its preset differs, not because the tree lists it.

The broker's Markets tree has eight headings and the book had four groups. Adding
the rest as labels would have been decoration - and a label with no behaviour
behind it is the shape this codebase keeps paying for: `group` decided weekend
trading until the perpetuals proved a commodity can trade Saturdays, and that
had to move to a per-symbol flag.

Equity CFDs are different in ways the presets carry: one cash session, a lot
step and minimum unlike an index, and a gap over every earnings date. "perp" was
left out on the same test - what distinguishes a perpetual is that it trades the
weekend, and that is already answered per symbol.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import GROUPS
from micofx.store import Store

PRESETS = json.loads((Path(__file__).resolve().parents[1] / "config" / "defaults.json")
                     .read_text(encoding="utf-8"))["group_presets"]


def test_stock_is_offered():
    assert "stock" in GROUPS


def test_stock_has_a_label():
    assert Store.GROUP_LABEL.get("stock")


def test_every_group_has_a_preset():
    """A group with no preset gives a new symbol the bare dataclass defaults."""
    missing = [g for g in GROUPS if g not in PRESETS]
    assert not missing, missing


def test_every_preset_has_a_group():
    """The reverse: a preset nobody can select is dead configuration."""
    orphan = [g for g in PRESETS if g not in GROUPS]
    assert not orphan, orphan


def test_the_stock_preset_actually_differs_from_the_index_one():
    """Otherwise it is the label this test exists to refuse."""
    assert PRESETS["stock"] != PRESETS["index"]


def test_perp_did_not_become_a_group():
    """What makes a perpetual different is answered by weekend_open per symbol."""
    assert "perp" not in GROUPS
