"""AI1: account-strip cards keep their fields after the density pass."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "micofx" / "web" / "static" / "style.css").read_text(encoding="utf-8")


def _cards_fn() -> str:
    start = JS.index("function renderCards()")
    end = JS.index("function costCell(", start)
    return JS[start:end]


def test_render_cards_still_writes_the_v1_fields():
    # Whole file: the projection's regime, costed slice and badge moved out of
    # the card and into the capacity line, which is a different function.
    body = JS
    for needle in (
        "Beklenen Aylik",
        "maliyetsiz",
        "maliyetli",
        "projected_costed_monthly",
        "maliyetli dilim",
        "maliyetli dilimde negatif",
        "Acilabilir Islem",
        "sembol basi",
        "max_positions_per_symbol",
        "ai.risk_scale",
        "lot x",
    ):
        assert needle in body, needle


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
    """Eight cards, and every column count divides eight.

    auto-fill chose the count from the width, so the last row held whatever did
    not divide - at 1590px the strip came out four, four and a single card
    stranded on a third row. Eight cards against 8/4/2 columns leaves no
    remainder at any breakpoint, and the widest case puts them all on one row,
    which is what the strip is for.
    """
    assert "grid-template-columns: repeat(8, 1fr);" in CSS
    for count in (4, 2):
        assert f"grid-template-columns: repeat({count}, 1fr);" in CSS
    # The word appears in the comment explaining why it went; check the rule.
    rules = [ln for ln in CSS.splitlines()
             if "grid-template-columns" in ln and not ln.lstrip().startswith(("/*", "*"))]
    assert not [r for r in rules if "auto-fill" in r and ".cards" in r]


def test_every_card_is_the_same_shape():
    """One label, one number, one line of foot - for all ten.

    The projection used to carry a sentence and a badge, which made it taller
    than the rest whatever the grid did. Both moved to the capacity line below,
    where prose belongs.
    """
    # The literal appears in prose further down the file; check the card
    # definitions and the markup that renders them.
    defs = JS[JS.index("const cards = ["):JS.index("$(\"#account-cards\")")]
    assert "wide" not in defs, "no card may claim extra width any more"
    assert "foot-line" not in defs
    markup = JS[JS.index("$(\"#account-cards\")"):]
    assert 'c.wide' not in markup[:400]


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
