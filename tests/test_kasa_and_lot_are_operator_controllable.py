"""Operator can size the book and park kasa without killing autopilot."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import AutoPilot
from scripts.kasa_auto import compute_kasa_targets

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _sys_keys() -> set[str]:
    start = APP_JS.index("const SYS_FIELDS")
    end = APP_JS.index("const MT5_PATH_FIELDS")
    return set(re.findall(r'\{ k:\s*"([^"]+)"', APP_JS[start:end]))


def test_lot_multiplier_is_on_the_system_panel():
    assert "lot_multiplier" in _sys_keys()


def test_kasa_auto_toggle_is_on_the_system_panel():
    assert "kasa_auto_enabled" in _sys_keys()


def test_advanced_holds_lot_and_concurrent():
    assert "SYS_FIELDS_ADVANCED" in APP_JS
    start = APP_JS.index("const SYS_FIELDS_ADVANCED")
    end = APP_JS.index("const MT5_PATH_FIELDS")
    body = APP_JS[start:end]
    assert "lot_multiplier" in body
    assert "max_concurrent_risk_pct" in body


def test_kasa_concurrent_stays_under_hard_max():
    plan = compute_kasa_targets(
        equity=250, leverage=500, n_enabled=6,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=85, lot_multiplier=1.0, max_concurrent_risk_pct=10,
        broker_leverage=500,
    )
    assert plan["targets"]["max_concurrent_risk_pct"] <= 50.0


def test_apply_kasa_skips_when_operator_disabled_it():
    eng = MagicMock()
    eng._account = {"equity": 250, "leverage": 500}
    eng._capacity_cache = {"rows": [], "global_free_slots": 1, "margin_usage_pct": 0}
    store = MagicMock()
    store.system = MagicMock(
        kasa_auto_enabled=False,
        lot_multiplier=1.2,
        max_margin_usage_pct=85.0,
        max_concurrent_risk_pct=10.0,
        target_leverage=50.0,
    )
    store.symbols = {}
    eng.store = store
    eng.client = MagicMock(connected=True)
    ap = AutoPilot(eng)
    assert ap._apply_kasa() == ["kasa: operator kapali"]
    store.update_system.assert_not_called()


def test_apply_kasa_does_not_patch_lot_or_concurrent():
    """Inline owns lot/conc — slow tick may only touch margin."""
    eng = MagicMock()
    eng._account = {"equity": 247, "leverage": 500}
    eng._capacity_cache = {"rows": [], "global_free_slots": 1, "margin_usage_pct": 0}
    store = MagicMock()
    store.system = MagicMock(
        kasa_auto_enabled=True,
        lot_multiplier=0.5,
        max_margin_usage_pct=20.0,
        max_concurrent_risk_pct=5.0,
        target_leverage=50.0,
    )
    store.symbols = {"A": MagicMock(enabled=True), "B": MagicMock(enabled=True)}
    store.get_setting = MagicMock(return_value=0)
    eng.store = store
    eng.client = MagicMock(connected=True)
    ap = AutoPilot(eng)
    ap._entry_rows = MagicMock(return_value=[])
    ap._enabled_symbols = MagicMock(return_value=["A", "B"])
    ap._apply_kasa()
    if store.update_system.called:
        patch = store.update_system.call_args[0][0]
        assert "lot_multiplier" not in patch
        assert "max_concurrent_risk_pct" not in patch
