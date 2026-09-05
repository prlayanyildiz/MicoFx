"""F6: stamped positive_ratio is holdout sub-window robustness, not selection 1.0."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.backtest import subwindow_positive_ratio


def test_subwindow_positive_ratio_counts_positive_parts():
    # Five up, one down → 5/6
    nets = [10.0, 5.0, 1.0, -2.0, 3.0, 4.0]

    def run_one(window):
        lo, _hi = window
        # window lo maps onto nets by index when we split 0..600 into 6*100
        idx = lo // 100
        return SimpleNamespace(net_r=nets[idx])

    ratio = subwindow_positive_ratio(run_one, (0, 600), parts=6)
    assert abs(ratio - 5 / 6) < 1e-9


def test_f1_pos_ratio_skips_legacy_one_point_zero():
    """Incumbent positive_ratio=1.0 is selection-era noise; do not demand 6/6."""
    import time
    from unittest.mock import MagicMock

    from micofx.models import SymbolConfig
    from micofx.optimizer import Optimizer

    cfg = SymbolConfig(symbol="GER40", magic=1, strategy="channel_break",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 86400
    cfg.opt_summary = {
        "holdout": {"net_r": 100.0, "score": 40.0},
        "positive_ratio": 1.0,
        "validated": True,
    }
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.symbols = {cfg.symbol: cfg}
    opt.store.system = MagicMock(charge_costs=False, block_high_cost=False)
    opt.store.opt_params.return_value = {"min_positive_ratio": 0.6}
    opt.store.get_setting.return_value = {"reopt_min_age_hours": 0.0}
    opt._force_apply = False
    opt._beats_incumbent = lambda cfg, hold: True
    opt._generalises = lambda best, symbol: True
    best = {
        "score": 10.0,
        "positive_ratio": 0.67,
        "min_positive_ratio": 0.6,
        "holdout": {
            "net_r": 116.0, "score": 8.0, "trades": 80,
            "expectancy": 0.1, "profit_factor": 1.2, "cost_per_trade_r": 0.01,
        },
        "validation": {
            "net_r": 116.0, "score": 9.0, "trades": 80,
            "expectancy": 0.1, "profit_factor": 1.2, "cost_per_trade_r": 0.01,
        },
    }
    assert opt.reject_reason(cfg, best, strategy="burst", timeframe="M30") == ""


def test_f1_pos_ratio_blocks_weaker_robustness_stamp():
    import time
    from unittest.mock import MagicMock

    from micofx.models import SymbolConfig
    from micofx.optimizer import Optimizer

    cfg = SymbolConfig(symbol="GER40", magic=1, strategy="channel_break",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 86400
    cfg.opt_summary = {
        "holdout": {"net_r": 100.0, "score": 40.0},
        "positive_ratio": 0.83,
        "validated": True,
    }
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.symbols = {cfg.symbol: cfg}
    opt.store.system = MagicMock(charge_costs=False, block_high_cost=False)
    opt.store.opt_params.return_value = {"min_positive_ratio": 0.6}
    opt.store.get_setting.return_value = {"reopt_min_age_hours": 0.0}
    opt._force_apply = False
    opt._beats_incumbent = lambda cfg, hold: True
    opt._generalises = lambda best, symbol: True
    best = {
        "score": 10.0,
        "positive_ratio": 0.50,
        "selection_positive_ratio": 1.0,
        "min_positive_ratio": 0.6,
        "holdout": {
            "net_r": 116.0, "score": 8.0, "trades": 80,
            "expectancy": 0.1, "profit_factor": 1.2, "cost_per_trade_r": 0.01,
        },
        "validation": {
            "net_r": 116.0, "score": 9.0, "trades": 80,
            "expectancy": 0.1, "profit_factor": 1.2, "cost_per_trade_r": 0.01,
        },
    }
    # Asserted as "refused, and the number is named", not as one Turkish word.
    # A ratio weaker than the incumbent's is caught by two different gates
    # depending on how weak it is - min_positive_ratio ("holdout dilimleri
    # kirilgan") below 0.6, and the family/TF-flip consistency gate
    # ("tutarlilik zayif") between 0.6 and the stamp's own 0.83. Pinning the
    # second gate's wording made the test fail when the first one legitimately
    # answered first, which says nothing about the property this file guards:
    # that a weaker robustness fraction cannot replace a stronger one.
    for weaker in (0.50, 0.67):
        best["positive_ratio"] = weaker
        reason = opt.reject_reason(cfg, best, strategy="burst", timeframe="M30")
        assert reason, f"positive_ratio {weaker} reddedilmedi (damga 0.83)"
        assert f"{weaker:.2f}" in reason, (
            f"red gerekcesi orani adlandirmiyor: {reason}")
    best["positive_ratio"] = 0.83
    assert opt.reject_reason(cfg, best, strategy="burst", timeframe="M30") == ""
