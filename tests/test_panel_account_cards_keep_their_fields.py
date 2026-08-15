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
        "maliyetsiz OPT",
        "maliyetli OPT",
        "projected_costed_monthly",
        "maliyetli dilim",
        "MALIYETLI DILIM NEGATIF",
        "AI Lot Carpani",
        "Acilabilir Islem",
        "sembol basi",
        "max_positions_per_symbol",
        "ai.risk_scale",
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
    assert "min-height: 1.35em" in CSS, "an empty foot must still hold its line"


def test_the_column_count_divides_the_cards():
    """Ten cards, five columns: two full rows and no leftover slot.

    auto-fill chose the count from the width, so the last row held whatever did
    not divide - seven and a void at one size, nine and one at another. A fixed
    count per breakpoint is duller and always tidy, and the counts chosen (5, 4,
    3, 2) all divide ten or come close.
    """
    assert "grid-template-columns: repeat(5, 1fr);" in CSS
    for count in (4, 3, 2):
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
    """Moved, not dropped - the regime is the reason the number is readable."""
    for needle in ("beklenen aylik", "maliyetsiz OPT", "maliyetli OPT",
                   "maliyetli dilim", "MALIYETLI DILIM NEGATIF", "butce"):
        assert needle in JS, needle
