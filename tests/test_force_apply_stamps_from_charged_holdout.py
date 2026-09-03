"""force=True apply may stamp from a live charged holdout when WFO left no detail.

GER40 channel_break A2 (03.09) produced ok sweeps that never validated (M30
hold +29 / val -9.8). Claude's charged cell sl1.5/ts1.5 still paid; force
must be able to land a measured retune without a walk-forward stamp.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


def test_force_apply_builds_stamp_from_charged_holdout():
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = True
    cfg = SymbolConfig(
        symbol="GER40", magic=1, enabled=True,
        strategy="channel_break", timeframe="M30",
        sl_atr_mult=1.0, trail_start_atr=2.0, trail_step_atr=2.2,
    )
    store = MagicMock()
    store.symbols = {"GER40": cfg}
    store.system = SystemConfig(charge_costs=True)
    store.opt_params.return_value = {"lookback_days": 180, "segments": 5}
    store.update_symbol = MagicMock(side_effect=lambda sym, patch, source="": (
        setattr(cfg, "sl_atr_mult", patch.get("sl_atr_mult", cfg.sl_atr_mult)) or
        setattr(cfg, "trail_start_atr", patch.get("trail_start_atr", cfg.trail_start_atr)) or
        cfg
    ))
    opt.store = store
    opt.client = MagicMock()
    opt.entry_lock = None
    opt._spread_scale = lambda sym: 1.0
    opt._holdout_costed = lambda *a, **k: {
        "trades": 200, "net_r": 58.0, "expectancy": 0.29, "score": 40.0,
        "profit_factor": 1.3, "cost_per_trade_r": 0.03, "cost_r": 6.0,
        "wins": 70, "losses": 130, "win_rate": 35.0, "max_dd_r": 20.0,
        "capture": 0.1, "exits": {},
    }
    opt.client.positions.return_value = []

    res = opt.apply(
        "GER40",
        {"sl_atr_mult": 1.5, "trail_start_atr": 1.5},
        score=0.0,
        detail=None,
        timeframe="M30",
        strategy="channel_break",
    )
    assert res.get("ok") is True, res
    store.update_symbol.assert_called()
    patch = store.update_symbol.call_args[0][1]
    assert patch["sl_atr_mult"] == 1.5
    assert patch["trail_start_atr"] == 1.5
    hold = (patch.get("opt_summary") or {}).get("holdout") or {}
    assert float(hold.get("net_r")) == 58.0
