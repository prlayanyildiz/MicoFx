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
    assert 'tab === "tani"' in JS or 'activeTab === "tani"' in JS
    assert "renderExecution()" in JS
    assert "renderLive()" in JS
    assert 'id="exec-table"' in HTML
    assert 'id="live-table"' in HTML


def test_autopsy_table_shows_cash_kar():
    """Flatten rows can have empty profit; R is still valid. Show both."""
    tani = _slice("page-tani", "page-opt")
    assert "th.autopsy.Kar" in tani
    assert "autopsy-table" in tani
    body = JS.split("async function loadAutopsies()", 1)[1].split(
        "async function ", 1)[0]
    assert "r.profit" in body
    assert 'rowsInto($("#autopsy-table")' in body
    assert ", 9)" in body or ", 9," in body


def test_autopsy_note_says_masada_is_winners_only():
    src = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py"
           ).read_text(encoding="utf-8")
    chunk = src[src.index("def trade_autopsies"): src.index(
        "def entry_blocks_reset")]
    assert "kazanan" in chunk.lower()


def test_live_table_carries_the_entry_block():
    """Tanı canlı satır: note boşken spread/lot kapısı görünmüyordu."""
    assert '"entry_block"' in JS or "st.entry_block" in JS
    eng = (Path(__file__).resolve().parents[1] / "micofx" / "engine.py"
           ).read_text(encoding="utf-8")
    keys = eng[eng.index("_PANEL_STATE_KEYS"): eng.index("_COOLDOWN_BARS")]
    assert "entry_block" in keys
