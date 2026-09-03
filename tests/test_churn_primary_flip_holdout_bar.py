"""Churn F1: family/TF flip needs a material holdout edge over the incumbent."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


def _opt(cfg: SymbolConfig) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.symbols = {cfg.symbol: cfg}
    opt.store.system = MagicMock(charge_costs=False, block_high_cost=False)
    opt.store.opt_params.return_value = {"min_positive_ratio": 0.6}
    opt.store.get_setting.return_value = {"reopt_min_age_hours": 0.0}
    opt._force_apply = False
    opt._beats_incumbent = lambda cfg, hold: True
    opt._generalises = lambda best, symbol: True
    return opt


def _best(hold_net: float, pos: float = 1.0) -> dict:
    return {
        "score": 10.0,
        "positive_ratio": pos,
        "min_positive_ratio": 0.6,
        "holdout": {
            "net_r": hold_net, "score": 8.0, "trades": 80,
            "expectancy": 0.1, "profit_factor": 1.2, "cost_per_trade_r": 0.01,
        },
        "validation": {
            "net_r": hold_net, "score": 9.0, "trades": 80,
            "expectancy": 0.1, "profit_factor": 1.2, "cost_per_trade_r": 0.01,
        },
    }


def test_family_flip_needs_fifteen_percent_more_holdout():
    cfg = SymbolConfig(symbol="GER40", magic=1, strategy="channel_break",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 86400
    cfg.opt_summary = {
        "holdout": {"net_r": 100.0, "score": 40.0},
        "positive_ratio": 1.0,
        "validated": True,
    }
    opt = _opt(cfg)
    # 110 < 115 → refuse
    reason = opt.reject_reason(cfg, _best(110.0), strategy="burst", timeframe="M30")
    assert "aile/TF flip" in reason
    # 116 >= 115 → pass F1 (other gates mocked open)
    reason = opt.reject_reason(cfg, _best(116.0), strategy="burst", timeframe="M30")
    assert reason == ""


def test_same_family_nudge_skips_the_flip_bar():
    cfg = SymbolConfig(symbol="GER40", magic=1, strategy="channel_break",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 86400
    cfg.opt_summary = {
        "holdout": {"net_r": 100.0, "score": 40.0},
        "positive_ratio": 1.0,
        "validated": True,
    }
    opt = _opt(cfg)
    reason = opt.reject_reason(cfg, _best(101.0), strategy="channel_break",
                               timeframe="M30")
    assert reason == ""


def test_family_flip_uses_costed_incumbent_net_when_stamp_was_paper():
    """A charged family flip must clear the incumbent's charged bar, not paper."""
    cfg = SymbolConfig(symbol="NAS100", magic=1, strategy="mtf_pullback",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 86400
    cfg.opt_summary = {
        "holdout": {"net_r": 172.58, "score": 116.06},
        "holdout_costed": {"net_r": 72.36, "score": 32.13},
        "positive_ratio": 1.0,
        "validated": True,
        "charge_costs": False,
    }
    opt = _opt(cfg)
    opt.store.system.charge_costs = True
    # 84 >= 72.36 * 1.15 ~= 83.2, but far below the inflated paper 198.5 bar.
    reason = opt.reject_reason(cfg, _best(84.0), strategy="burst", timeframe="M30")
    assert reason == ""


def test_none_candidate_pr_is_not_selection_inconsistency():
    """Force stamp / unmeasured holdout pr must not read as 0% of windows."""
    cfg = SymbolConfig(symbol="NAS100", magic=1, strategy="mtf_pullback",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 86400
    cfg.opt_summary = {
        "holdout": {"net_r": 100.0, "score": 40.0},
        "positive_ratio": None,
        "selection_positive_ratio": None,
        "validated": True,
    }
    opt = _opt(cfg)
    best = _best(101.0, pos=None)
    best["selection_positive_ratio"] = None
    reason = opt.reject_reason(cfg, best, strategy="mtf_pullback",
                               timeframe="M30")
    assert reason != "secim segmentleri arasinda tutarsiz"
    assert reason == ""
