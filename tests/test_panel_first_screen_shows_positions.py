"""AJ: first-look blocks sit above the 13-column capacity table."""
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


def test_open_positions_and_day_sit_above_capacity():
    body = _panel()
    assert body.index("positions-table") < body.index("capacity-table")
    assert body.index("day-table") < body.index("capacity-table")
    assert body.index("account-cards") < body.index("positions-table")


def test_capacity_table_still_has_its_thirteen_columns():
    body = _panel()
    for header in (
        "Sembol", "Grup", "Durum", "Lot", "Avantaj", "Lot Modu",
        "Acik", "Limit", "Acilabilir", "Marj / Islem", "Risk / Islem (1R)",
        "Maliyet / Islem", "Beklenen / Islem", "Acik K/Z",
    ):
        assert header in body, header


def test_capacity_summary_can_wrap():
    assert "capacity-summary" in CSS or "#capacity-summary" in CSS
