"""Idle must not beat a much stronger charged edge in slot races.

Live at $232 (~2 seats): JPN225 costed e=0.239 idle prio 1.53 lost to
NAS100 e=0.046 ok prio 1.59 — state tax 0.55 vs 1.0 outweighed 5x edge.
Unproven (idle) is not weak; watch/quarantine stay punitive.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor, SymbolVerdict


class _SettingsStore:
    def get_setting(self, key, default=None):
        return dict(DEFAULTS) if key == "supervisor" else default


def _sup() -> Supervisor:
    s = object.__new__(Supervisor)
    s._lock = threading.RLock()
    s.store = _SettingsStore()
    s.verdicts = {}
    s.optimizer = None
    return s


def _cfg(sym: str, exp: float) -> SymbolConfig:
    return SymbolConfig(
        symbol=sym,
        opt_summary={
            "holdout": {"expectancy": exp, "net_r": exp * 100, "trades": 100},
            "holdout_costed": {
                "expectancy": exp, "net_r": exp * 100, "trades": 100,
            },
        },
        opt_score=20.0,
    )


def test_strong_idle_beats_weak_ok_in_priority():
    jpn = _cfg("JPN225", 0.239)
    nas = _cfg("NAS100", 0.046)
    sup = _sup()
    idle = SymbolVerdict(symbol="JPN225", state="idle")
    ok = SymbolVerdict(symbol="NAS100", state="ok", trades=5, expectancy=-1.0)
    # Not enough trades for live bonus on NAS (needs min_trades//2)
    ok.trades = 2
    ok.expectancy = -5.0
    assert sup.priority(jpn, idle) > sup.priority(nas, ok)
