"""The 3s poll must not rebuild innerHTML when the view has not moved.

Live books still rebuild when profit/SL/cycle change. A quiet/stopped
panel should not thrash the DOM.
"""
from __future__ import annotations

from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static"
      / "app.js").read_text(encoding="utf-8")


def test_refresh_skips_unchanged_panel_dom():
    body = JS.split("async function refresh()", 1)[1].split("async function ", 1)[0]
    assert "viewPulse" in body
    assert "lastViewPulse" in body
    assert "renderTop()" in body
