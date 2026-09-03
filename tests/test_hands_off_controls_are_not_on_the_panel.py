"""Operator hands-off controls do not live on the terminal.

27.08: cost toggles left first. The rest of the same class - plumbing,
search-gate internals, supervisor knobs, strategy-signal guts - were still
one click away behind "Ileri duzey". They stay on Store / engine / opt;
the panel must not offer them.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "micofx" / "web" / "templates" / "index.html").read_text(encoding="utf-8")

KEEP_SYS = (
    "max_margin_usage_pct",
    "max_concurrent_risk_pct",
    "daily_loss_pct",
    "lot_multiplier",
    "kasa_auto_enabled",
    "target_leverage",
)

HANDS_OFF_SYS = (
    "max_total_positions",
    "max_positions",
    "max_lot",
    "trade_all_hours", "day_end_flatten_min",
    "close_on_stop", "autostart_bot", "daily_profit_pct",
    "max_scalp_positions", "max_swing_positions",
    "min_free_margin", "slippage_points",
    "poll_interval_sec", "opt_max_workers",
    "autostart_mt5_wait_sec",
    "backup_enabled",
    "size_by_edge", "daily_loss_flatten",
)

KEEP_BACKUP = ("backup_dir", "backup_dir_secondary", "backup_keep")
KEEP_MT5_PATH = "mt5_terminal_path"
KEEP_MT5_AUTOSTART = "autostart_mt5"


def _block(name: str) -> str:
    start = APP_JS.index(f"const {name}")
    nxt = APP_JS.find("\nconst ", start + 1)
    if nxt < 0:
        nxt = APP_JS.find("\nfunction ", start + 1)
    return APP_JS[start:nxt]


def _keys(name: str) -> set[str]:
    return set(re.findall(r'\{ k:\s*"([^"]+)"', _block(name)))


def test_hands_off_system_dials_are_not_on_the_panel():
    keys = _keys("SYS_FIELDS") | _keys("SYS_FIELDS_ADVANCED")
    keys |= _keys("BACKUP_FIELDS") | _keys("MT5_PATH_FIELDS")
    for k in HANDS_OFF_SYS:
        assert k not in keys, f"{k} still has a panel control"
    for k in KEEP_SYS:
        assert k in keys, f"{k} left the operator list"


def test_mt5_path_is_editable_on_the_connection_panel():
    assert KEEP_MT5_PATH in _keys("MT5_PATH_FIELDS")
    assert KEEP_MT5_AUTOSTART in _keys("MT5_PATH_FIELDS")
    assert KEEP_MT5_PATH not in _keys("SYS_FIELDS")
    assert KEEP_MT5_AUTOSTART not in _keys("SYS_FIELDS")
    assert 'id="sys-mt5-path"' in HTML
    assert "sys-mt5-path" in APP_JS
    assert "Ayarlanan yol" not in APP_JS


def test_backup_path_and_keep_live_on_bot_control():
    for k in KEEP_BACKUP:
        assert k in _keys("BACKUP_FIELDS")
        assert k not in _keys("SYS_FIELDS")
    assert 'id="sys-backup"' in HTML
    assert "sys-backup" in APP_JS


def test_search_gate_internals_are_not_on_the_panel():
    assert "OPT_SETTING_FIELDS_ADVANCED" not in APP_JS
    assert "opt-settings-advanced" not in HTML
    assert "opt-grid" not in HTML
    assert "Parametre Izgarasi" not in HTML
    assert "SWING_OVERLAY" not in APP_JS
    assert "SYS_DANGER_NOTES" not in APP_JS
    assert "syncSysDangerNotes" not in APP_JS
    assert "btn-opt-reset" not in APP_JS


def test_supervisor_knobs_are_not_on_the_panel():
    assert "id=\"ai-settings\"" not in HTML
    assert "Denetleyici Ayarlari" not in HTML


def test_saving_opt_params_does_not_wipe_the_grid():
    src = APP_JS[APP_JS.index("async function saveOptParams"):]
    src = src[:src.index("\nasync function ")]
    assert "body.grid = {}" not in src
    assert "if (Object.keys(grid).length) body.grid = grid" in src


def test_stop_overlays_are_not_on_the_symbol_card():
    """Operator 27.08: readout was noise. Hours stay. Search still writes exits."""
    start = APP_JS.index("function buildSymbolCard")
    card = APP_JS[start:APP_JS.index("function applySymbolFilter")]
    assert "Stop ve Overlay" not in card
    assert "EXIT_SECTION" not in APP_JS
    assert "function buildReadout" not in APP_JS
    assert "sl_atr_mult" not in card
    assert "Ileri duzey / Strateji" not in card
    assert "Pozisyon Boyutu" not in card
    assert "const POSITION_SECTION" not in APP_JS
    assert 'k: "max_lot"' not in card
    assert 'k: "max_margin_pct"' not in card
    assert 'k: "max_positions"' not in card
    assert 'k: "risk_percent"' not in card
    assert 'k: "lot_mode"' not in card
    assert 'k: "fixed_lot"' not in card
    assert "Islem Saatleri" in card
    assert "Varsayilana Don" not in card


def test_dead_symbol_guts_ui_is_gone():
    """Hands-off left the defs. They had zero callers; restore is a trap."""
    assert "const SECTIONS" not in APP_JS
    assert "function optFieldVisible" not in APP_JS
    assert "function loadSchema" not in APP_JS
    assert "ADVANCED_SECTIONS" not in APP_JS
    assert "loadSymbols().then(refresh)" in APP_JS
    assert "dataset.aiKey" not in APP_JS
