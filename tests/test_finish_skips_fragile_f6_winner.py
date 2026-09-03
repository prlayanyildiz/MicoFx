"""Winner pick must skip F6-fragile validated sweeps for a robust peer.

US30 costed_e re-WFO (03.09) named channel_break/M5 (holdout 3/6) as best,
then reject_reason refused apply — leave a robust M30 peer on the table.
Filter F6 before _pick_by_validation so apply_best can land the robust one.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


def _attempt(tf: str, hold_pr: float, val_score: float, order: int) -> dict:
    return {
        "ok": True,
        "validated": True,
        "order": order,
        "timeframe": tf,
        "strategy": "channel_break",
        "best": {
            "score": val_score,
            "positive_ratio": hold_pr,
            "selection_positive_ratio": 1.0,
            "min_positive_ratio": 0.7,
            "params": {"sl_atr_mult": 1.5 if tf == "M5" else 2.5,
                       "trail_start_atr": 0.3 if tf == "M5" else 0.8},
            "validation": {
                "net_r": 20.0, "trades": 50, "profit_factor": 1.2,
                "expectancy": 0.2, "score": val_score,
                "cost_per_trade_r": 0.05,
            },
            "holdout": {
                "net_r": 22.0 if tf == "M5" else 40.0, "trades": 50,
                "profit_factor": 1.3, "expectancy": 0.25, "score": val_score,
                "cost_per_trade_r": 0.05,
            },
            "selection": {
                "net_r": 50.0, "trades": 100, "profit_factor": 1.3,
                "expectancy": 0.3, "score": 30.0,
            },
        },
    }


def test_finish_symbol_picks_robust_peer_over_fragile_higher_val():
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = True
    opt._cancel = MagicMock()
    opt._cancel.is_set.return_value = False
    opt.job = {"source": "manual"}
    cfg = SymbolConfig(
        symbol="US30", magic=1, enabled=True,
        strategy="channel_break", timeframe="M30",
        sl_atr_mult=2.5, trail_start_atr=0.8,
        opt_updated_at=1.0,
        opt_summary={"holdout": {"net_r": 43.0, "score": 34.0,
                                 "profit_factor": 1.37, "trades": 276},
                     "validated": True},
    )
    store = MagicMock()
    store.symbols = {"US30": cfg}
    store.system = SystemConfig(charge_costs=True)
    store.opt_params.return_value = {"min_positive_ratio": 0.7}
    store.get_setting.return_value = {"reopt_min_age_hours": 0}
    store.record_opt_run = MagicMock()
    store.update_symbol = MagicMock(side_effect=lambda sym, patch, source="": cfg)
    opt.store = store
    opt.client = MagicMock()
    opt.client.positions.return_value = []
    opt.entry_lock = None
    opt._spread_scale = lambda sym: 1.0
    opt._holdout_costed = lambda *a, **k: {
        "trades": 50, "net_r": 40.0, "expectancy": 0.25, "score": 20.0,
        "profit_factor": 1.3, "cost_per_trade_r": 0.05, "cost_r": 2.5,
        "wins": 20, "losses": 30, "win_rate": 40.0, "max_dd_r": 5.0,
        "capture": 0.1, "exits": {},
    }
    # Fragile M5 has higher validation score; robust M30 must win the pick.
    plan = {
        "cfg": cfg,
        "started": 0.0,
        "error": None,
        "attempts": [
            _attempt("M5", 0.5, val_score=30.0, order=0),
            _attempt("M30", 1.0, val_score=20.0, order=1),
        ],
    }
    report = opt._finish_symbol(plan, apply_best=True)
    assert report.get("timeframe") == "M30", report
    assert float((report.get("best") or {}).get("positive_ratio") or 0) >= 0.7
