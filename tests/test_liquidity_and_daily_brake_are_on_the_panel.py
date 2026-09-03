"""Operator can dial concurrent risk and daily loss from Sistem again.

27.08 hid them with the plumbing dump. Backend still honours both
(_OPERATOR_SYSTEM_FIELDS). Operator asked for the liquidity box + brake
control on the panel (Claude 03.09 12:02).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _sys_keys() -> set[str]:
    start = APP_JS.index("const SYS_FIELDS")
    end = APP_JS.index("const SYS_FIELDS_ADVANCED")
    return set(re.findall(r'\{ k:\s*"([^"]+)"', APP_JS[start:end]))


def test_concurrent_risk_is_on_the_system_panel():
    assert "max_concurrent_risk_pct" in _sys_keys()


def test_daily_loss_brake_is_on_the_system_panel():
    assert "daily_loss_pct" in _sys_keys()
