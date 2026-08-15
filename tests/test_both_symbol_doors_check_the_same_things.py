"""A field must not be accepted at two strictnesses depending on the button.

Audit slice 7 (15.08) found the symbol editor and the bulk editor disagreeing:
``PATCH /api/symbols/{symbol}`` validated indicator periods against
``_INDICATOR_PERIOD_BOUNDS``, ``POST /api/symbols-bulk`` did not. Same field,
same store, two different gates - the same shape as backtest's stop floor, where
``simulate`` read a zero as a floor of zero and ``walk_forward`` read it as ten
points.

The same slice found ``symbol_daily_loss_pct`` with no range at all: a
per-symbol daily loss gate, live risk, and the only such field the panel let
through raw. Zero disables it, so zero is legal; past 100 it can never fire,
which reads as "set" and behaves as "off".
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.web.app import _INDICATOR_PERIOD_BOUNDS, _SYMBOL_RISK_BOUNDS

APP = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py").read_text(
    encoding="utf-8")


def _door(name: str) -> str:
    start = APP.index(f"def {name}(")
    end = APP.index("    @app.", start)
    return APP[start:end]


def test_the_daily_loss_gate_has_a_range():
    assert "symbol_daily_loss_pct" in _SYMBOL_RISK_BOUNDS, (
        "a live-risk field with no bounds is one hand-typed value from being off")
    lo, hi, inclusive = _SYMBOL_RISK_BOUNDS["symbol_daily_loss_pct"]
    assert lo == 0.0 and inclusive, "zero disables the gate and must stay legal"
    assert hi <= 100.0, "a percentage above 100 can never fire"


def test_the_bulk_door_checks_indicator_periods_too():
    body = _door("bulk_patch")
    assert "_INDICATOR_PERIOD_BOUNDS" in body, (
        "the single PATCH checks these; the bulk door accepted them raw")


def test_both_doors_run_the_same_checks():
    """Whatever the list becomes, the two doors have to agree on it."""
    single, bulk = _door("patch_symbol"), _door("bulk_patch")
    for check in ("_reject_internal_fields", "_validate_enum_fields",
                  "_validate_risk_bounds", "_validate_sessions",
                  "_INDICATOR_PERIOD_BOUNDS"):
        assert check in single, f"{check} missing from the single-symbol door"
        assert check in bulk, f"{check} missing from the bulk door"


def test_the_indicator_table_is_not_empty():
    """The assertions above would pass vacuously against an empty table."""
    assert len(_INDICATOR_PERIOD_BOUNDS) >= 5
