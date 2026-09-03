"""target_leverage is retired from the panel; kasa_leverage helper stays capped."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import kasa_leverage

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _sys_keys() -> set[str]:
    start = APP_JS.index("const SYS_FIELDS")
    end = APP_JS.index("const MT5_PATH_FIELDS")
    return set(re.findall(r'\{ k:\s*"([^"]+)"', APP_JS[start:end]))


def test_target_leverage_is_not_on_the_system_panel():
    assert "target_leverage" not in _sys_keys()


def test_margin_pct_is_primary_dial():
    assert "max_margin_usage_pct" in _sys_keys()


def test_zero_target_uses_broker_leverage():
    sys = MagicMock(target_leverage=0.0)
    assert kasa_leverage(sys, {"leverage": 200}) == 200.0


def test_target_is_capped_to_broker_ceiling():
    sys = MagicMock(target_leverage=1000.0)
    assert kasa_leverage(sys, {"leverage": 200}) == 200.0
