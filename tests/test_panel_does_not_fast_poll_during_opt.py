"""The panel must not poll /api/state faster while a search is running.

refresh() used to drop from 3s to 1.5s when opt.state==running, which is
exactly when the engine, workers, and the panel already share one MT5 lock.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "micofx" / "web" / "static" / "app.js"


def test_the_panel_keeps_the_three_second_poll_during_a_search():
    src = APP_JS.read_text(encoding="utf-8")
    assert "fast ? 1500" not in src
    assert "hidden ? 6000 : 3000" in src
