"""A group the book accepts must be selectable in the panel that adds symbols.

"stock" was added to models.GROUPS, store.GROUP_LABEL and the presets, and the
panel still offered four - because the options were typed into two <select>
blocks in the template and a third copy of the labels lived in app.js. Four
places, one list, and adding to two of them looked complete.

Same shape as the rest of today: the symbol editor and the bulk editor running
different validations, create and patch disagreeing about whether a symbol may
be enabled, simulate and walk_forward reading a zero stop floor two ways. The
options are generated from one map now, so the panel cannot fall behind the
book.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import GROUPS
from micofx.store import Store

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "micofx" / "web" / "templates" / "index.html").read_text(encoding="utf-8")


def _js_labels() -> dict:
    body = JS[JS.index("const GROUP_LABEL = {"):]
    body = body[:body.index("};")]
    return dict(re.findall(r"(\w+):\s*\"([^\"]+)\"", body))


def test_the_panel_knows_every_group_the_book_accepts():
    missing = [g for g in GROUPS if g not in _js_labels()]
    assert not missing, missing


def test_the_panel_invents_no_group_of_its_own():
    extra = [g for g in _js_labels() if g not in GROUPS]
    assert not extra, extra


def test_the_labels_match_the_server_side_ones():
    assert _js_labels() == Store.GROUP_LABEL


def test_no_group_options_are_typed_into_the_template():
    """A hardcoded <option> is how the panel fell behind in the first place."""
    for group in GROUPS:
        assert f'<option value="{group}">' not in HTML, group


def test_the_selects_are_marked_for_filling():
    assert HTML.count('data-groups=') >= 2
    assert "fillGroupSelects()" in JS


def test_an_equity_ticker_guesses_the_stock_group():
    """The broker's equity CFDs carry a market suffix: AAPL.US, SMSN.KR."""
    guess = JS[JS.index("function guessGroup"):]
    guess = guess[:guess.index("\n}")]
    assert 'return "stock"' in guess
    assert "US|KR|CN" in guess
