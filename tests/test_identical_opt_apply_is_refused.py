"""Identical opt apply payloads must not rewrite the live stamp."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


def _opt(cfg: SymbolConfig) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.symbols = {cfg.symbol: cfg}
    opt.store.system = MagicMock(charge_costs=False)
    opt.store.opt_params.return_value = {}
    opt.store.get_setting.return_value = {}
    opt._force_apply = False
    opt._holdout_costed = lambda *a, **k: None
    opt._apply_stamp_missing = lambda detail: None
    opt.holdout_retention = lambda detail: 1.0
    opt._charge_costs_stamp = lambda detail: False
    opt._spread_scale = lambda symbol: 1.0
    return opt


def test_identical_apply_is_refused_as_unchanged():
    cfg = SymbolConfig(symbol="GER40", magic=1, strategy="channel_break",
                       timeframe="M30", sl_atr_mult=1.5, trail_start_atr=1.0,
                       trail_step_atr=0.8)
    cfg.opt_updated_at = 1.0
    cfg.opt_summary = {
        "holdout": {"net_r": 42.0, "score": 20.0, "trades": 100},
        "params": {"sl_atr_mult": 1.5, "trail_start_atr": 1.0, "trail_step_atr": 0.8},
        "validated": True, "charge_costs": False, "spread_scale": 1.0,
    }
    cfg.validated = True
    opt = _opt(cfg)
    opt.entry_lock = None
    detail = {
        "holdout": {"net_r": 42.0, "score": 20.0, "trades": 100},
        "validation": {"net_r": 50.0, "score": 25.0, "trades": 80},
        "selection": {"net_r": 100.0},
        "params": {"sl_atr_mult": 1.5, "trail_start_atr": 1.0, "trail_step_atr": 0.8},
        "charge_costs": False, "spread_scale": 1.0, "validated": True,
        "holdout_days": 30.0, "positive_ratio": 1.0,
        "min_positive_ratio": 0.7, "grid_total": 1, "max_combos": 1,
        "coverage": 1.0, "combo_seed": 7, "combos": 1,
    }
    res = opt.apply("GER40",
                    {"sl_atr_mult": 1.5, "trail_start_atr": 1.0, "trail_step_atr": 0.8},
                    20.0, detail=detail, timeframe="M30", strategy="channel_break")
    assert res.get("ok") is False
    assert "degismedi" in (res.get("error") or "").lower() or res.get("unchanged") is True
    opt.store.update_symbol.assert_not_called()
