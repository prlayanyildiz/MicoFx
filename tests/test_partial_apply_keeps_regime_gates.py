"""Partial force apply must not zero live regime gates (US30 03.09 23:59).

Passing only blocked_entry_hours let absent_regime_gates_to_zero wipe
adx_min 20->0 and crushed the charged stamp +25R -> +10R.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


def test_partial_force_apply_keeps_live_adx_min():
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = True
    cfg = SymbolConfig(
        symbol="US30", magic=1, enabled=True,
        strategy="channel_break", timeframe="M30",
        sl_atr_mult=2.0, trail_start_atr=0.5, trail_step_atr=2.2,
        adx_min=20.0, blocked_entry_hours=[],
    )
    store = MagicMock()
    store.symbols = {"US30": cfg}
    store.system = SystemConfig(charge_costs=True)
    store.opt_params.return_value = {"lookback_days": 180, "segments": 5}
    written = {}

    def _upd(sym, patch, source=""):
        written.update(patch)
        for k, v in patch.items():
            if hasattr(cfg, k) and k != "opt_summary":
                setattr(cfg, k, v)
        return cfg

    store.update_symbol = MagicMock(side_effect=_upd)
    opt.store = store
    opt.client = MagicMock()
    opt.client.connected = True
    opt.client.positions.return_value = []
    opt.entry_lock = None
    opt._spread_scale = lambda sym: 1.0
    opt._holdout_costed = lambda *a, **k: {
        "trades": 200, "net_r": 22.0, "expectancy": 0.11, "score": 15.0,
        "profit_factor": 1.2, "cost_per_trade_r": 0.03, "cost_r": 6.0,
        "wins": 80, "losses": 120, "win_rate": 40.0, "max_dd_r": 20.0,
        "capture": 0.1, "exits": {}, "holdout_days": 400.0,
    }

    res = opt.apply(
        "US30",
        {"blocked_entry_hours": [13, 16, 21]},
        score=0.0,
        detail=None,
        timeframe="M30",
        strategy="channel_break",
    )
    assert res.get("ok") is True, res
    assert written.get("blocked_entry_hours") == [13, 16, 21]
    # Must not wipe the live ADX gate on a partial retune.
    assert float(written.get("adx_min", cfg.adx_min)) == 20.0
