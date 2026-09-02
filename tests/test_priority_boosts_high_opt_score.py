"""Same-cycle slot races should prefer the higher walk-forward opt_score."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor


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


def test_higher_opt_score_wins_when_holdout_edge_is_equal():
    hold = {"expectancy": 0.15, "net_r": 50.0, "trades": 300}
    gold = SymbolConfig(
        symbol="XAUUSD",
        opt_score=60.0,
        opt_summary={"holdout": hold},
    )
    ger = SymbolConfig(
        symbol="GER40",
        opt_score=33.0,
        opt_summary={"holdout": hold},
    )
    sup = _sup()
    assert sup.priority(gold) > sup.priority(ger)
