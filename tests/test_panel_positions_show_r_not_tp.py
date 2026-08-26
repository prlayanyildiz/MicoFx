"""The positions grid must show live R, not a TP column that is always zero.

Constitution: tp=0 always. The leftover 69R on winners was invisible on the
first screen because the row carried dollars and an empty TP. Harvest sits
next to the open book, and the opt Test-R cell titles capture when present.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "micofx" / "web" / "templates" / "index.html").read_text(
    encoding="utf-8")
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
HELP = (ROOT / "micofx" / "web" / "static" / "field_help.js").read_text(
    encoding="utf-8")


def _positions_thead() -> str:
    start = HTML.index('id="positions-table"')
    return HTML[start:HTML.index("</thead>", start)]


def test_positions_table_has_r_and_mfe_instead_of_tp():
    head = _positions_thead()
    assert 'data-help="th.pos.R"' in head
    assert 'data-help="th.pos.MFE"' in head
    assert 'data-help="th.pos.Durum"' in head
    assert 'data-help="th.pos.TP"' not in head
    assert "harvest-note" in HTML


def test_render_positions_paints_r_open_and_giveback():
    body = JS.split("function renderPositions()", 1)[1].split(
        "function renderDayTable()", 1)[0]
    assert "p.r_open" in body
    assert "p.mfe_r" in body
    assert "partial_done" in body
    assert "harvest-note" in JS or "renderHarvest" in JS
    assert "p.tp" not in body or "price(p.tp" not in body


def test_opt_test_r_titles_capture_when_present():
    body = JS.split("function renderOptJob()", 1)[1].split(
        "async function loadOptHistory()", 1)[0]
    assert "h.capture" in body


def test_r_help_says_original_stop_not_cash():
    text = HELP.split('"th.pos.R"', 1)[1].split('"', 2)[1]
    low = text.lower()
    assert "orijinal" in low or "original" in low or "ilk stop" in low
    assert "r" in low
