"""Cost switches stay on in the engine; they are not panel dials.

Measured 27.08 on this book: ``block_high_cost`` at 18% refused 0 of 909
signals because ``max_spread_atr`` is tighter. ``charge_costs`` on is the
honest search (US30 holdout edge ~equals the spread it actually pays). The
two checkboxes were flipped from the terminal and that was the confusion.
The flags remain on ``SystemConfig``; search and ``_try_entry`` still read
them. The companion percent left with them so it cannot be twiddled without
the gate.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SystemConfig

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")

def _block(name: str) -> str:
    start = APP_JS.index(f"const {name}")
    nxt = APP_JS.find("\nconst ", start + 1)
    if nxt < 0:
        nxt = APP_JS.find("\nfunction ", start + 1)
    return APP_JS[start:nxt]


def _sys_keys() -> set[str]:
    keys = re.findall(r'\{ k:\s*"([^"]+)"', _block("SYS_FIELDS"))
    keys += re.findall(r'\{ k:\s*"([^"]+)"', _block("SYS_FIELDS_ADVANCED"))
    return set(keys)


def test_the_two_cost_toggles_are_not_on_the_panel():
    keys = _sys_keys()
    for k in ("block_high_cost", "charge_costs"):
        assert k not in keys, f"{k} still has a panel control"


def test_the_percent_companion_left_with_them():
    assert "max_cost_pct_of_risk" not in _sys_keys()


def test_the_engine_still_owns_the_flags():
    cfg = SystemConfig()
    assert hasattr(cfg, "block_high_cost")
    assert hasattr(cfg, "charge_costs")
    assert hasattr(cfg, "max_cost_pct_of_risk")
