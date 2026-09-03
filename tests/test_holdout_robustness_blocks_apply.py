"""F6 holdout robustness must block apply even when selection was consistent.

US30 costed_e WFO (id662) applied channel_break/M5 with positive_ratio 0.5
(3/6 fragile) because reject_reason only gated selection_positive_ratio.
Claude 03.09: min_positive_ratio must bind the F6 stamp too (force included).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


def _opt() -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = False
    opt.store = MagicMock()
    opt.store.system = SystemConfig(charge_costs=True)
    opt.store.opt_params.return_value = {"min_positive_ratio": 0.7}
    opt.store.symbols = {
        "US30": SymbolConfig(symbol="US30", magic=1, strategy="channel_break",
                             timeframe="M30"),
    }
    return opt


def test_reject_reason_refuses_fragile_holdout_positive_ratio():
    opt = _opt()
    cfg = opt.store.symbols["US30"]
    best = {
        "score": 20.0,
        "positive_ratio": 0.5,  # F6 holdout 3/6
        "selection_positive_ratio": 1.0,  # selection looked fine
        "min_positive_ratio": 0.7,
        "validation": {
            "net_r": 10.0, "trades": 40, "profit_factor": 1.2, "expectancy": 0.2,
            "cost_per_trade_r": 0.02,
        },
        "holdout": {
            "net_r": 22.0, "trades": 40, "profit_factor": 1.2, "expectancy": 0.2,
            "cost_per_trade_r": 0.02,
        },
        "selection": {"net_r": 50.0, "trades": 100, "profit_factor": 1.3,
                      "expectancy": 0.3},
    }
    reason = opt.reject_reason(cfg, best, strategy="channel_break", timeframe="M5")
    assert reason, "fragile holdout must be refused"
    assert "kirilgan" in reason or "tutarsiz" in reason or "holdout" in reason.lower()


def test_reject_reason_allows_robust_holdout_positive_ratio():
    opt = _opt()
    cfg = opt.store.symbols["US30"]
    best = {
        "score": 20.0,
        "positive_ratio": 1.0,
        "selection_positive_ratio": 1.0,
        "min_positive_ratio": 0.7,
        "validation": {
            "net_r": 10.0, "trades": 40, "profit_factor": 1.2, "expectancy": 0.2,
            "cost_per_trade_r": 0.02,
        },
        "holdout": {
            "net_r": 43.0, "trades": 40, "profit_factor": 1.3, "expectancy": 0.3,
            "cost_per_trade_r": 0.02,
        },
        "selection": {"net_r": 50.0, "trades": 100, "profit_factor": 1.3,
                      "expectancy": 0.3},
    }
    reason = opt.reject_reason(cfg, best, strategy="channel_break", timeframe="M30")
    # may still refuse on age/incumbent etc. — must NOT be the fragility reason
    assert reason != "secim segmentleri arasinda tutarsiz"
    if reason:
        assert "kirilgan" not in reason


def test_apply_force_refuses_fragile_holdout_stamp():
    """HTTP force skips reject_reason — apply() must still block 3/6."""
    opt = _opt()
    opt._force_apply = True
    opt.store.update_symbol = MagicMock()
    opt.client = MagicMock()
    opt.client.positions.return_value = []
    opt.entry_lock = None
    opt._spread_scale = lambda sym: 1.0
    opt._holdout_costed = lambda *a, **k: {
        "trades": 40, "net_r": 22.0, "expectancy": 0.2, "score": 10.0,
        "profit_factor": 1.2, "cost_per_trade_r": 0.02, "cost_r": 0.8,
        "wins": 20, "losses": 20, "win_rate": 50.0, "max_dd_r": 5.0,
        "capture": 0.1, "exits": {},
    }
    detail = {
        "holdout": {
            "net_r": 22.0, "trades": 40, "profit_factor": 1.2, "expectancy": 0.2,
            "cost_per_trade_r": 0.02,
        },
        "validation": {
            "net_r": 10.0, "trades": 40, "profit_factor": 1.2, "expectancy": 0.2,
        },
        "selection": {"net_r": 50.0, "trades": 100},
        "holdout_days": 90.0,
        "validated": True,
        "positive_ratio": 0.5,
        "selection_positive_ratio": 1.0,
        "min_positive_ratio": 0.7,
    }
    res = opt.apply(
        "US30",
        {"sl_atr_mult": 1.0, "trail_start_atr": 0.8},
        score=20.0,
        detail=detail,
        timeframe="M5",
        strategy="channel_break",
    )
    assert res.get("ok") is False, res
    assert "kirilgan" in str(res.get("error", ""))
    opt.store.update_symbol.assert_not_called()
