"""Autopsy 'masada' is giveback on winners, not mfe-minus-loss on losers.

26.08: left>=1 painted 97/138 red; 70 of those were losers. A losing
stop cannot 'leave 2.6R on the table'. Stored left_on_table_r is unchanged.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
HELP = (ROOT / "micofx" / "web" / "static" / "field_help.js").read_text(
    encoding="utf-8")


def test_autopsy_panel_shows_left_on_table_only_for_winners():
    body = JS.split("async function loadAutopsies()", 1)[1].split(
        "async function ", 1)[0]
    assert "Number(r.r_realised) > 0 && Number(r.left_on_table_r) >= 1" in body
    assert "Number(r.r_realised) > 0 && r.left_on_table_r != null" in body


def test_masada_help_says_winners_only_and_mfe_is_not_harvestable():
    text = HELP.split('"th.autopsy.Masada"', 1)[1].split('"', 2)[1]
    low = text.lower()
    assert "kazanan" in low
    assert "hasat" in low or "bar" in low
