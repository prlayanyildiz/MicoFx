"""A hard AI refusal must not judge config B by config A's 30-day record.

Soft sizing (0.6x) may remember the full window. A ``return False`` may not:
it may read judged_trades / judged_pf, or something config-independent
(quarantine state, hour-of-day). ``verdict.trades`` / ``profit_factor`` /
``expectancy`` are the full lookback and belong to whatever configs ran
inside it.

The docstring distinction: **kisma hatirlar, red hatirlamaz**.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import Supervisor, SymbolVerdict


class _Store:
    def get_setting(self, key, default=None):
        return {"enabled": True, "prefer_strong_on_dd": True, "min_trades": 25,
                "hard_block_only_quarantine": False}


def _sup(risk_scale: float = 0.4) -> Supervisor:
    s = Supervisor.__new__(Supervisor)
    s.store = _Store()
    s.risk_scale = risk_scale
    s.verdicts = {}
    return s


def _gate(sup: Supervisor, v: SymbolVerdict):
    sup.verdicts[v.symbol] = v
    return Supervisor._gate_locked(sup, SymbolConfig(symbol=v.symbol), 1786728000.0)


def _poisoned() -> SymbolVerdict:
    """Full-window record of a deleted config, current config unproven."""
    v = SymbolVerdict(symbol="NAS100", state="ok", reason="")
    v.trades = 72
    v.expectancy = -1.699
    v.profit_factor = 0.4
    v.judged_trades = 0
    v.judged_pf = 0.0
    v.risk_scale = 1.0
    return v


def test_full_window_poison_does_not_refuse():
    allowed, reason, scale = _gate(_sup(), _poisoned())
    assert allowed is True, reason
    assert scale > 0


def test_each_full_window_field_alone_cannot_refuse():
    """Drive the live function; do not list refuse branches by hand."""
    for field, value in (("trades", 999), ("expectancy", -99.0), ("profit_factor", 0.01)):
        v = _poisoned()
        setattr(v, field, value)
        v.judged_trades, v.judged_pf = 0, 2.0
        v.state = "ok"
        allowed, reason, _ = _gate(_sup(), v)
        assert allowed is True, f"{field}={value} refused: {reason}"


def test_judged_negative_still_refuses():
    v = _poisoned()
    v.judged_trades, v.judged_pf = 30, 0.72
    allowed, reason, _ = _gate(_sup(), v)
    assert allowed is False
    assert "negatif" in reason


def test_refuse_source_does_not_read_the_full_window_fields():
    """A new refuse branch that consults trades/expectancy/PF fails this."""
    src = inspect.getsource(Supervisor._gate_locked)
    # Strip comments so historical narration does not count as a read.
    code = "\n".join(
        line for line in src.splitlines()
        if not line.lstrip().startswith("#")
    )
    for needle in ("verdict.trades", "verdict.expectancy", "verdict.profit_factor"):
        assert needle not in code, f"refuse path still reads {needle}"
