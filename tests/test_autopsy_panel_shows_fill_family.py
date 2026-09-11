"""Autopsy panel must show fill-time strategy + TF (Claude KOL-2 11.09).

Past 427 rows are unattributable; from note_fill stamp onward the close
row carries strategy/timeframe. The panel had neither column, so the
attribution Claude landed in the book was invisible.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "micofx" / "web" / "templates" / "index.html").read_text(
    encoding="utf-8")
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def test_autopsy_table_headers_include_family_and_tf():
    start = HTML.index('id="autopsy-table"')
    end = HTML.index("</thead>", start)
    head = HTML[start:end]
    assert "th.autopsy.Aile" in head
    assert "th.autopsy.TF" in head


def test_autopsy_rows_render_strategy_and_timeframe():
    body = JS.split("async function loadAutopsies()", 1)[1].split(
        "async function ", 1)[0]
    assert "r.strategy" in body
    assert "r.timeframe" in body
    assert ", 11)" in body or ", 11," in body
