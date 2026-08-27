"""AI1: account-strip cards keep their fields after the density pass."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "micofx" / "web" / "static" / "style.css").read_text(encoding="utf-8")
HTML = (ROOT / "micofx" / "web" / "templates" / "index.html").read_text(encoding="utf-8")


def test_the_v1_fields_survived_the_move_to_the_top_bar():
    """Operator 26.08: the strip is gone; its four gauges are top-bar chips.

    ``Acilabilir Islem`` is not in the list any more - it folded into the
    ``Pozisyon`` chip, which carries free slots and per-symbol cap in its
    label. Every other number the cards owned still has to exist somewhere.
    """
    body = JS
    for needle in (
        "Beklenen Aylik",
        "maliyetsiz",
        "maliyetli",
        "projected_costed_monthly",
        "maliyet odenmeden",
        "kagit/maliyetli fark",
        "maliyetli dilim",
        "maliyetli dilimde negatif",
        "ai.risk_scale",
        "lot x",
        "Marj Kullanimi",
    ):
        assert needle in body, needle
    assert "renderCards" not in JS, "card strip is gone; nothing may still call it"
    assert 'id="account-cards"' not in HTML


def test_stock_group_has_the_same_kind_of_pill_as_the_others():
    assert ".pill.stock" in CSS
    for group in (".pill.forex", ".pill.index", ".pill.commodity", ".pill.crypto"):
        assert group in CSS


def test_the_leftover_card_does_not_stretch_across_a_row():
    """auto-fit collapses the empty tracks and the last card fills the width.

    That was half of "kutular buyuk": one card ending up as wide as the strip.
    auto-fill keeps the tracks, so a card stays a card.
    """
    assert "auto-fill" in CSS
    assert "minmax(" in CSS


def test_the_cards_in_a_row_share_one_height():
    """The other half was a ragged edge.

    align-items:start let each card stop at its own content, so a strip where
    two cards carried three lines of foot and eight carried one looked
    scattered. Those two feet are one line now (the detail is unchanged in the
    capacity block below), so a shared row height is short for everyone.
    """
    assert "align-items: stretch" in CSS
    assert "min-height: 1.3" in CSS, "an empty foot must still hold its line"


def test_the_column_count_divides_the_cards():
    """AI strip is five readouts on one row.

    Was four account gauges until those moved to the top bar. The remaining
    ``.cards`` node is ``#ai-cards``. Five columns, one row; they shrink
    instead of wrapping a leftover sixth (Global Lot Carpani) onto a
    second line.
    """
    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in CSS
    rules = [ln for ln in CSS.splitlines()
             if "grid-template-columns" in ln and not ln.lstrip().startswith(("/*", "*"))]
    assert not [r for r in rules if "auto-fill" in r and ".cards" in r]


def test_every_gauge_chip_is_the_same_shape():
    """One label, one number, an optional bar - for all thirteen chips.

    A gauge's detail is a sentence, and a sentence in the chip label is what
    pushed the bar to three rows. The chip keeps the deciding number; the
    sentence lives in the hover title. Same trade the capacity line makes.
    """
    defs = JS[JS.index("const items = ["):JS.index('$("#topstats").innerHTML')]
    assert "signed(costed)" in defs, (
        "headline must be the charged figure, not the paper one")
    assert "Number(cap.projected_costed_monthly) || paper" in JS
    assert "overlayMonthlyProjection" in JS
    assert 'sub: "kagit"' in defs, (
        "the % sits next to live P/L otherwise; paper must be on the chip")
    assert "sub: `%${num(projPct" not in defs
    assert "tip:" in defs, "gauge detail belongs in the hover title"
    assert "foot-line" not in defs
    markup = JS[JS.index('$("#topstats").innerHTML'):]
    assert 'class="bar"' in markup[:700], "a chip must be able to carry a bar"


def test_the_projection_detail_survived_the_move():
    """Moved, not dropped - the regime is the reason the number is readable.

    The figure itself stayed on the card, so the capacity line stopped repeating
    it; what the line keeps is the part no card carries - which regime the
    projection was measured under, and its charged counterpart.
    """
    for needle in ("maliyetsiz", "maliyetli", "maliyetli dilim",
                   "marj butcesi", "projeksiyon"):
        assert needle in JS, needle


def test_the_capacity_line_stops_repeating_the_cards():
    """It was the longest line on the page, made of numbers already read."""
    line = JS[JS.index('$("#capacity-summary").innerHTML'):]
    line = line[:line.index(";", line.index("costedNote"))]
    for repeated in ("pozisyon dolu", "slot bos", "beklenen aylik"):
        assert repeated not in line, f"{repeated} is on a card already"


def test_the_costed_badge_does_not_contradict_the_sum():
    """It fired on any symbol going negative while the total read positive.

    "maliyetli dilim +634,16 | MALIYETLI DILIM NEGATIF" on one line is a
    contradiction to anyone reading it; the flag is per symbol and the figure is
    a sum, so the badge has to say which of the two it is talking about.
    """
    assert "bazi semboller maliyetli dilimde negatif" in JS
    assert "MALIYETLI DILIM NEGATIF" not in JS


def test_there_is_one_density_and_no_toggle():
    """Operator 27.08: roomy is the panel, not a preference.

    Two spacing sets meant the screenshot in a bug report and the screen in
    front of the operator could disagree, and the choice lived in localStorage
    where neither of us could see it. The knobs stayed - they are how a size
    change is one edit - but there is a single column of them now.

    ``btn-log-density`` is a different control on the Log tab (line height for
    a wall of text) and is deliberately not covered here.
    """
    assert ':root[data-density=' not in CSS, "one set of knobs, no second column"
    assert 'id="btn-density"' not in HTML
    assert "micofx-density" not in JS, "no stored preference to diverge from"
    assert "dataset.density" not in JS
    assert "--d-tstat-y" in CSS, "the knobs themselves stay"


def test_the_sticky_offsets_match_the_bar_they_were_measured_against():
    """The tab strip sticks at --d-topbar-h; a stale literal overlaps the bar.

    Measured 27.08 at 1440-1920px with the chips on one row: topbar 73.1px,
    tabs 39.5px, main padding 2x16px, status strip 40px. The two numbers are
    rounded up so the strip never lands on top of the bar and the log page
    never grows past the viewport.
    """
    knobs = CSS[CSS.index("--d-main:"):CSS.index("* { box-sizing")]
    topbar = int(re.search(r"--d-topbar-h:\s*(\d+)px", knobs).group(1))
    chrome = int(re.search(r"--d-chrome:\s*(\d+)px", knobs).group(1))
    assert topbar >= 74, "the roomy bar is 73.1px tall"
    assert chrome >= topbar + 39 + 32 + 40
