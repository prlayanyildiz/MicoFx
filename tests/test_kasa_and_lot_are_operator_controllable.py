"""Operator can size the book and park kasa without killing autopilot.

Capacity diagnosis 03.09: kasa was rewriting lot_multiplier every 15m and
targeting concurrent 50. Panel needs the lot dial; kasa needs its own off
switch; concurrent target caps at 25.
"""
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
    end = APP_JS.index("const SYS_FIELDS_ADVANCED")
    return set(re.findall(r'\{ k:\s*"([^"]+)"', APP_JS[start:end]))


def test_lot_multiplier_is_on_the_system_panel():
    assert "lot_multiplier" in _sys_keys()


def test_kasa_auto_toggle_is_on_the_system_panel():
    assert "kasa_auto_enabled" in _sys_keys()


def test_kasa_concurrent_target_caps_at_25():
    plan = compute_kasa_targets(
        equity=250, leverage=500, n_enabled=6,
        global_free_slots=1, margin_usage_pct=0,
        max_margin_usage_pct=85, lot_multiplier=1.0, max_concurrent_risk_pct=10,
    )
    assert plan["targets"]["max_concurrent_risk_pct"] <= 25.0


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
    )
    store.symbols = {}
    eng.store = store
    eng.client = MagicMock(connected=True)
    ap = AutoPilot(eng)
    assert ap._apply_kasa() == ["kasa: operator kapali"]
    store.update_system.assert_not_called()
