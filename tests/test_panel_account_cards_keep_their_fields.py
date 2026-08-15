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
    body = _cards_fn()
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


def test_account_cards_size_to_content_not_a_fixed_row():
    """auto-fit stretched the leftover card across the next row."""
    assert "auto-fill" in CSS
    assert "align-items: start" in CSS
    assert "minmax(" in CSS


def test_the_projection_card_gets_two_tracks():
    """One card carries a sentence; the rest carry a number.

    auto-fill stops cards stretching but leaves empty slots at the end of the
    last row - the "bos yerler" half of the complaint. The projection card is
    the only one that wants more width (regime label, costed counterpart,
    negative badge), so it takes one of those slots instead of wrapping its
    text into a paragraph that sets the row's height.
    """
    assert ".card.wide { grid-column: span 2; }" in CSS
    assert "wide: true" in JS, "no card claims the span"
    assert 'c.wide ? "wide "' in JS, "the class never reaches the markup"


def test_the_span_collapses_on_a_narrow_screen():
    """Two tracks out of two is the whole row - worse than not spanning."""
    assert "@media (max-width: 700px) { .card.wide { grid-column: span 1; } }" in CSS
