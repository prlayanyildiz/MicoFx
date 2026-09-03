"""Churn F2: soft dwell window needs a material holdout jump."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


def _opt(cfg: SymbolConfig, *, force: bool = False) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.symbols = {cfg.symbol: cfg}
    opt.store.system = MagicMock(charge_costs=False, block_high_cost=False)
    opt.store.opt_params.return_value = {"min_positive_ratio": 0.6}
    # Soft dwell only — hard settle off so F2 is visible.
    opt.store.get_setting.return_value = {"reopt_min_age_hours": 0.0}
    opt._force_apply = force
    opt._beats_incumbent = lambda cfg, hold: True
    opt._generalises = lambda best, symbol: True
    return opt


def _best(hold_net: float) -> dict:
    return {
        "score": 10.0,
        "positive_ratio": 1.0,
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


def test_dwell_blocks_small_holdout_jump_inside_12h():
    cfg = SymbolConfig(symbol="GOLD-PERP", magic=1, strategy="mtf_pullback",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 3 * 3600
    cfg.opt_summary = {"holdout": {"net_r": 100.0}, "positive_ratio": 1.0}
    opt = _opt(cfg)
    reason = opt.reject_reason(cfg, _best(110.0), strategy="mtf_pullback",
                               timeframe="M30")
    assert "dwell" in reason or "churn dwell" in reason


def test_dwell_allows_twenty_five_percent_holdout_jump():
    cfg = SymbolConfig(symbol="GOLD-PERP", magic=1, strategy="mtf_pullback",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 3 * 3600
    cfg.opt_summary = {"holdout": {"net_r": 100.0}, "positive_ratio": 1.0}
    opt = _opt(cfg)
    reason = opt.reject_reason(cfg, _best(130.0), strategy="mtf_pullback",
                               timeframe="M30")
    assert reason == ""


def test_force_bypasses_dwell():
    cfg = SymbolConfig(symbol="GOLD-PERP", magic=1, strategy="mtf_pullback",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 3 * 3600
    cfg.opt_summary = {"holdout": {"net_r": 100.0}, "positive_ratio": 1.0}
    opt = _opt(cfg, force=True)
    reason = opt.reject_reason(cfg, _best(105.0), strategy="mtf_pullback",
                               timeframe="M30")
    assert reason == ""
