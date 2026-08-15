"""AK2: Kayma and live-state tables move to Tani; IDs stay."""
from __future__ import annotations

from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "templates"
        / "index.html").read_text(encoding="utf-8")
JS = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static"
      / "app.js").read_text(encoding="utf-8")


def _slice(start_id: str, end_id: str) -> str:
    start = HTML.index(f'id="{start_id}"')
    end = HTML.index(f'id="{end_id}"', start)
    return HTML[start:end]


def test_exec_and_live_tables_are_on_tani_not_panel():
    panel = _slice("page-panel", "page-semboller")
    tani = _slice("page-tani", "page-opt")
    assert "exec-table" not in panel
    assert "live-table" not in panel
    assert "exec-table" in tani
    assert "live-table" in tani
    assert "positions-table" in panel
    assert "day-table" in panel
    assert "capacity-table" in panel


def test_refresh_still_fills_exec_and_live_on_tani():
    assert 'activeTab === "tani"' in JS
    assert "renderExecution()" in JS
    assert "renderLive()" in JS
    assert 'id="exec-table"' in HTML
    assert 'id="live-table"' in HTML
