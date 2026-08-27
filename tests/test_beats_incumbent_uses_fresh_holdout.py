"""Incumbent comparison used a stale opt_summary.holdout stamp, not the
same window the candidate just ran. Found 15.08 overnight: JPN225's
candidate scored 27.97 on the current holdout and lost to a stamp of
160.64 from a longer, older slice (SpotBrent stamp n=1532 vs AO1 n=722
is the same class). The live config must be replayed on that window;
the stamp is only a fallback when the replay is unavailable.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self):
        self.system = type("S", (), {"charge_costs": True})()


def _opt(*, fresh):
    opt = object.__new__(Optimizer)
    opt.store = _Store()
    opt._spread_scale = lambda symbol: 1.0
    if fresh is not None:
        opt._holdout_costed = lambda *a, **k: fresh
    return opt


def _cfg(stamp_score=160.64):
    cfg = SymbolConfig(symbol="JPN225", magic=1, strategy="stoch_flip",
                       timeframe="M15")
    cfg.opt_summary = {
        "holdout": {"score": stamp_score, "trades": 1532},
        "spread_scale": 1.0,
        "charge_costs": True,
    }
    cfg.opt_updated_at = time.time() - 86400
    return cfg


def test_same_config_stamp_vs_fresh_disagreement_uses_fresh():
    """Candidate 27.97 loses to stamp 160 but beats a same-window live 20."""
    opt = _opt(fresh={"score": 20.0, "trades": 80})
    assert opt._beats_incumbent(_cfg(), {"score": 27.97}) is True
    assert opt._beats_incumbent(_cfg(), {"score": 19.0}) is False


def test_fresh_replay_unavailable_falls_back_to_the_stamp():
    """object.__new__ Optimizer has no client; a raised replay must not
    invent a win, or the existing stamp-based tests lose their bar."""
    opt = _opt(fresh=None)

    def _boom(*a, **k):
        raise RuntimeError("no bars")

    opt._holdout_costed = _boom
    assert opt._beats_incumbent(_cfg(160.64), {"score": 27.97}) is False
    assert opt._beats_incumbent(_cfg(160.64), {"score": 161.0}) is True


def test_an_unvalidated_stamp_cannot_block_a_weaker_candidate():
    """GAP-5 wrote validated=false and +38 score. Fresh replay is often
    missing inside a worker (allow_fetch=False). The stamp then froze
    NAS100 on a config live 30d had already judged PF 0.50."""
    opt = _opt(fresh=None)

    def _boom(*a, **k):
        raise RuntimeError("no bars")

    opt._holdout_costed = _boom
    cfg = _cfg(38.715)
    cfg.validated = False
    cfg.opt_summary["validated"] = False
    assert opt._beats_incumbent(cfg, {"score": 12.0}) is True


def test_an_unvalidated_row_still_defends_a_fresh_positive_replay():
    """GER40 is also GAP-5 unvalidated but the live replay still pays.
    Dropping the stamp must not also drop a same-window bar."""
    opt = _opt(fresh={"score": 20.0, "trades": 80})
    cfg = _cfg(38.715)
    cfg.validated = False
    cfg.opt_summary["validated"] = False
    assert opt._beats_incumbent(cfg, {"score": 27.97}) is True
    assert opt._beats_incumbent(cfg, {"score": 19.0}) is False
