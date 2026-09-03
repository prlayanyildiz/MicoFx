"""Refuse blocked_entry_hours retunes that worsen the charged holdout stamp.

Claude 04.09 00:05: NAS[17] −11.9R and XAU[16] −22.3R vs []; JPN[14,15]
+3.1R OK. Book-wide autopsy hours are not a live apply signal.
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


def test_blocked_hours_force_refuses_worse_charged_stamp():
    cfg = SymbolConfig(
        symbol="NAS100", magic=1, enabled=True,
        strategy="mtf_pullback", timeframe="M30",
        sl_atr_mult=0.5, trail_start_atr=0.3, trail_step_atr=2.5,
        adx_min=0.0, blocked_entry_hours=[],
        opt_summary={"holdout": {"net_r": 110.4, "trades": 700, "score": 64.0},
                     "holdout_days": 500.0, "validated": True},
    )
    opt = _opt(cfg, {
        "trades": 600, "net_r": 98.5, "expectancy": 0.16, "score": 51.0,
        "profit_factor": 1.18, "cost_per_trade_r": 0.03, "cost_r": 18.0,
        "wins": 200, "losses": 400, "win_rate": 33.0, "max_dd_r": 50.0,
        "capture": 0.1, "exits": {}, "holdout_days": 500.0,
    })
    res = opt.apply(
        "NAS100", {"blocked_entry_hours": [17]},
        score=0.0, detail=None, timeframe="M30", strategy="mtf_pullback",
    )
    assert res.get("ok") is False
    assert "blocked_entry_hours" in (res.get("error") or "")
    opt.store.update_symbol.assert_not_called()


def test_blocked_hours_force_allows_improvement():
    cfg = SymbolConfig(
        symbol="JPN225", magic=1, enabled=True,
        strategy="burst", timeframe="M30",
        sl_atr_mult=0.7, trail_start_atr=0.3, trail_step_atr=2.8,
        blocked_entry_hours=[],
        opt_summary={"holdout": {"net_r": 143.7, "trades": 373, "score": 122.0},
                     "holdout_days": 500.0, "validated": True},
    )
    opt = _opt(cfg, {
        "trades": 358, "net_r": 146.7, "expectancy": 0.41, "score": 126.0,
        "profit_factor": 1.6, "cost_per_trade_r": 0.03, "cost_r": 10.0,
        "wins": 150, "losses": 208, "win_rate": 42.0, "max_dd_r": 40.0,
        "capture": 0.1, "exits": {}, "holdout_days": 500.0,
    })
    res = opt.apply(
        "JPN225", {"blocked_entry_hours": [14, 15]},
        score=0.0, detail=None, timeframe="M30", strategy="burst",
    )
    assert res.get("ok") is True, res
    opt.store.update_symbol.assert_called()
