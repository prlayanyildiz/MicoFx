"""Validated paper incumbents must defend with charged holdout when available.

NAS100/JPN225/XAUUSD shipped with ``validated=True`` and a paper ``holdout``
score at the summary root, plus an already-stored charged ``holdout_costed``.
Charged re-WFO candidates were then compared against the larger paper number
and froze on "mevcut ayardan zayif" before they could reach the real bar.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, charge: bool = True):
        self.system = type("S", (), {"charge_costs": charge})()


def _opt(charge: bool = True, fresh: dict | None = None) -> Optimizer:
    opt = object.__new__(Optimizer)
    opt.store = _Store(charge)
    opt._spread_scale = lambda symbol: 1.0
    if fresh is not None:
        opt._holdout_costed = lambda *a, **k: fresh
    return opt


def _cfg() -> SymbolConfig:
    cfg = SymbolConfig(symbol="NAS100", magic=1, strategy="mtf_pullback", timeframe="M30")
    cfg.opt_updated_at = time.time() - 86400
    cfg.validated = True
    cfg.opt_summary = {
        "validated": True,
        "charge_costs": False,
        "spread_scale": 1.0,
        "holdout": {"score": 116.06, "net_r": 172.58, "trades": 1643},
        "holdout_costed": {"score": 32.13, "net_r": 72.36, "trades": 1559},
    }
    return cfg


def test_validated_paper_incumbent_uses_stored_costed_score_bar():
    """A charged candidate only needs to beat the charged incumbent score."""
    opt = _opt(charge=True, fresh=None)
    cfg = _cfg()
    assert opt._beats_incumbent(cfg, {"score": 33.0}) is True
    assert opt._beats_incumbent(cfg, {"score": 31.0}) is False


def test_validated_paper_incumbent_still_prefers_fresh_same_window_replay():
    """Stored costed holdout is the fallback; fresh replay remains the tighter bar."""
    opt = _opt(charge=True, fresh={"score": 40.0, "trades": 80})
    cfg = _cfg()
    assert opt._beats_incumbent(cfg, {"score": 39.0}) is False
    assert opt._beats_incumbent(cfg, {"score": 41.0}) is True
