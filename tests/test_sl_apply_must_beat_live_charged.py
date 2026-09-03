"""Refuse sl_atr_mult retunes that worsen the charged holdout stamp.

Premature-stop autopsy wants wider stops; bar-charged holdout often
rewards 0.5. Force-apply must not spend the live charged stamp (NAS/XAU
04.09 collapse) — WFO with the >=0.9 floor is the honest widen path.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


def _opt(cfg: SymbolConfig, measured: dict) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = True
    store = MagicMock()
    store.symbols = {cfg.symbol: cfg}
    store.system = SystemConfig(charge_costs=True)
    store.opt_params.return_value = {"lookback_days": 180, "segments": 5}
    store.update_symbol = MagicMock(return_value=cfg)
    store.get_setting = MagicMock(return_value={})
    opt.store = store
    opt.client = MagicMock()
    opt.client.connected = True
    opt.client.positions.return_value = []
    opt.entry_lock = None
    opt._spread_scale = lambda sym: 1.0
    opt._holdout_costed = lambda *a, **k: dict(measured)
    return opt


def test_sl_widen_force_refuses_worse_charged_stamp():
    cfg = SymbolConfig(
        symbol="NAS100", magic=1, enabled=True,
        strategy="mtf_pullback", timeframe="M30",
        sl_atr_mult=0.5, trail_start_atr=0.3, trail_step_atr=2.5,
        blocked_entry_hours=[],
        opt_summary={"holdout": {"net_r": 101.3, "trades": 739, "score": 64.0},
                     "holdout_days": 500.0, "validated": True},
    )
    opt = _opt(cfg, {
        "trades": 500, "net_r": 36.0, "expectancy": 0.07, "score": 20.0,
        "profit_factor": 1.05, "cost_per_trade_r": 0.03, "cost_r": 15.0,
        "wins": 180, "losses": 320, "win_rate": 36.0, "max_dd_r": 60.0,
        "capture": 0.1, "exits": {}, "holdout_days": 500.0,
    })
    res = opt.apply(
        "NAS100", {"sl_atr_mult": 1.0},
        score=0.0, detail=None, timeframe="M30", strategy="mtf_pullback",
    )
    assert res.get("ok") is False
    assert "sl_atr_mult" in (res.get("error") or "")
    opt.store.update_symbol.assert_not_called()


def test_sl_retune_allows_charged_improvement():
    cfg = SymbolConfig(
        symbol="GER40", magic=1, enabled=True,
        strategy="channel_break", timeframe="M30",
        sl_atr_mult=1.0, trail_start_atr=1.5, trail_step_atr=2.2,
        adx_min=0.0, blocked_entry_hours=[],
        opt_summary={"holdout": {"net_r": 71.0, "trades": 400, "score": 55.0},
                     "holdout_days": 500.0, "validated": True},
    )
    opt = _opt(cfg, {
        "trades": 374, "net_r": 72.8, "expectancy": 0.19, "score": 58.0,
        "profit_factor": 1.34, "cost_per_trade_r": 0.03, "cost_r": 11.0,
        "wins": 140, "losses": 234, "win_rate": 37.0, "max_dd_r": 18.0,
        "capture": 0.1, "exits": {}, "holdout_days": 500.0,
    })
    res = opt.apply(
        "GER40", {"sl_atr_mult": 1.5, "adx_min": 15.0},
        score=0.0, detail=None, timeframe="M30", strategy="channel_break",
    )
    assert res.get("ok") is True, res
