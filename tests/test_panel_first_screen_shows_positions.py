"""AJ: capacity + day share the top row, positions sits full-width below."""
from __future__ import annotations

from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "templates"
        / "index.html").read_text(encoding="utf-8")
CSS = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static"
       / "style.css").read_text(encoding="utf-8")


def _panel() -> str:
    start = HTML.index('id="page-panel"')
    end = HTML.index('id="page-semboller"', start)
    return HTML[start:end]


def test_panel_day_positions_top_capacity_below():
    """Operator 27.08: Gunluk Ozet + Pozisyonlar top row, capacity full-width.

    Gunluk Ozet (five columns) sits in a narrow 480px left column of the top
    ``.split`` and Pozisyonlar fills the space to its right. Islem Kapasitesi is
    a separate full-width panel below, so its 13 columns never scroll sideways.
    Earlier tries (capacity+day side by side, then a full stack) both looked
    wrong; this keeps the wide capacity table on its own row. The account-card
    strip is still gone - its gauges are chips in ``#topstats``.
    """
    body = _panel()
    assert "Pozisyonlar" in body
    assert "Acik Pozisyonlar" not in body
    assert body.index("day-table") < body.index("positions-table")
    assert body.index("positions-table") < body.index("capacity-table")
    assert "account-cards" not in body


def test_capacity_table_still_has_its_columns():
    body = _panel()
    for header in (
        "Sembol", "Grup", "Durum", "Lot", "Avantaj", "Lot notu",
        "Acik", "Acilabilir", "Marj / Islem", "Risk / Islem (1R)",
        "Maliyet / Islem", "Beklenen / Islem", "Acik K/Z",
    ):
        assert header in body, header
    assert ">Limit<" not in body
    assert "Lot Modu" not in body


def test_capacity_summary_can_wrap():
    assert "capacity-summary" in CSS or "#capacity-summary" in CSS
