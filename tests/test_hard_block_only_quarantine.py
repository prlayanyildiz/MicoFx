"""Hard AI refuse must not cut fills the walk-forward already counted.

Found in live ``entry_blocks`` (AX, 46.3h): 156 signals, 35 fills, 34
``ai_gate``. ``supervisor.gate`` runs only in ``engine._try_entry``;
``simulate`` never sees it. GER40 was the book's only clear cash winner
(+65$) and sat on watch at 0.5x because PF 2.53→0.92 looked like decay;
NAS100 at −122$ stayed ok 1.0x. Relative change, not dollars.

Default ``hard_block_only_quarantine``: watch / idle / blocked hours /
quarantine / prefer_strong_on_dd only scale lot. False restores the old
refusals.
"""
from __future__ import annotations

import calendar
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import Supervisor, SymbolVerdict


class _Store:
    def get_setting(self, key, default=None):
        return {
            "enabled": True,
            "prefer_strong_on_dd": True,
            "min_trades": 25,
            "hard_block_only_quarantine": True,
        }


def _sup(risk_scale: float = 0.5) -> Supervisor:
    s = Supervisor.__new__(Supervisor)
    s.store = _Store()
    s.risk_scale = risk_scale
    s.verdicts = {}
    return s


def _gate(sup: Supervisor, v: SymbolVerdict, server_now: float = 1786728000.0):
    sup.verdicts[v.symbol] = v
    return Supervisor._gate_locked(sup, SymbolConfig(symbol=v.symbol), server_now)


def test_watch_on_drawdown_scales_and_does_not_refuse():
    """prefer_strong_on_dd + watch used to set entry_block=ai_gate."""
    v = SymbolVerdict(symbol="GER40", state="watch", reason="kenar zayifliyor")
    v.judged_trades = 30
    v.risk_scale = 0.5
    allowed, reason, scale = _gate(_sup(0.5), v)
    assert allowed is True, reason
    assert scale < 1.0
    assert "ai_gate" not in reason


def test_blocked_hour_does_not_refuse():
    v = SymbolVerdict(symbol="XAUUSD", state="ok", reason="")
    v.blocked_hours = [10]
    v.hour_risk_scales = {10: 0.5}
    v.risk_scale = 1.0
    at_ten = calendar.timegm((2026, 8, 10, 10, 30, 0, 0, 0, 0))
    allowed, reason, scale = _gate(_sup(1.0), v, at_ten)
    assert allowed is True, reason
    assert scale <= 0.5


def test_quarantine_scales_not_refuses():
    v = SymbolVerdict(symbol="NAS100", state="quarantine", reason="PF cok dusuk")
    v.quarantine_until = time.time() + 3600
    v.risk_scale = 0.0
    allowed, reason, scale = _gate(_sup(1.0), v)
    assert allowed is True, reason
    assert scale == 0.6
    assert "karantina" in reason
