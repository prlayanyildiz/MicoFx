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


def test_positions_table_still_has_no_tp_column():
    """Operator 26.08 dropped the R and MFE columns from the open book.

    What this file was really guarding survives that: tp is always 0 by
    constitution, so a TP column would be a permanently empty one. R stays
    reachable - the status pill still reads ``p.r_open`` and the autopsy
    grid still carries realised R and MFE per closed trade.
    """
    head = _positions_thead()
    assert 'data-help="th.pos.TP"' not in head
    assert 'data-help="th.pos.Durum"' in head
    assert 'data-help="th.pos.R"' not in head
    assert 'data-help="th.pos.MFE"' not in head
    assert "harvest-note" in HTML


def test_render_positions_still_reads_r_for_the_status_pill():
    body = JS.split("function renderPositions()", 1)[1].split(
        "function renderDayTable()", 1)[0]
    assert "p.r_open" in body, "harvest/BE pill decides on open R"
    assert "partial_done" in body
    assert "harvest-note" in JS or "renderHarvest" in JS
    assert "p.tp" not in body or "price(p.tp" not in body


def test_the_dropped_columns_left_no_orphan_help():
    assert '"th.pos.R"' not in HELP
    assert '"th.pos.MFE"' not in HELP


def test_opt_test_r_titles_capture_when_present():
    body = JS.split("function renderOptJob()", 1)[1].split(
        "async function loadOptHistory()", 1)[0]
    assert "h.capture" in body


