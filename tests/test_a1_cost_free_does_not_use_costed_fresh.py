"""Cost-free search must not beat a costed incumbent replay (A1 churn).

Live ``charge_costs=False`` scores candidates on paper. ``_fresh_incumbent_holdout``
used to always call ``_holdout_costed``, which depressed the live config and
let every mediocre paper candidate look like an upgrade.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


def _opt(charge: bool, *, costed_fresh: dict | None):
    opt = object.__new__(Optimizer)
    opt.store = type("S", (), {
        "system": type("Sys", (), {"charge_costs": charge})(),
    })()
    opt._spread_scale = lambda symbol: 1.0
    opt._holdout_costed = lambda *a, **k: costed_fresh
    return opt


def _cfg(stamp_score: float = 50.0):
    cfg = SymbolConfig(symbol="NAS100", magic=1, strategy="mtf_pullback",
                       timeframe="M30")
    cfg.opt_summary = {
        "holdout": {"score": stamp_score, "trades": 80},
        "spread_scale": 1.0,
        "charge_costs": False,
    }
    cfg.opt_updated_at = time.time() - 3600
    return cfg


def test_cost_free_book_ignores_costed_fresh_and_uses_the_stamp():
    # Costed fresh would be 5; stamp is 50. Candidate 40 must lose to stamp,
    # not win against the depressed costed replay.
    opt = _opt(False, costed_fresh={"score": 5.0, "trades": 80})
    assert opt._fresh_incumbent_holdout(_cfg()) is None
    assert opt._beats_incumbent(_cfg(), {"score": 40.0}) is False
    assert opt._beats_incumbent(_cfg(), {"score": 55.0}) is True


def test_charging_book_still_uses_costed_fresh():
    opt = _opt(True, costed_fresh={"score": 20.0, "trades": 80})
    cfg = _cfg(160.0)
    cfg.opt_summary["charge_costs"] = True
    assert opt._fresh_incumbent_holdout(cfg) == {"score": 20.0, "trades": 80}
    assert opt._beats_incumbent(cfg, {"score": 27.0}) is True
    assert opt._beats_incumbent(cfg, {"score": 19.0}) is False
