"""When F6 drops every validated sweep, name the fragile ratios in keep_reason.

JPN225 04.09 WFO ended as opaque \"hicbir aday kapidan gecmedi\" while
tried rows carried hold_pr — Claude could not tell F6 from empty search.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


def test_finish_names_f6_when_all_validated_sweeps_are_fragile():
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = True
    opt._cancel = MagicMock()
    opt._cancel.is_set.return_value = False
    opt.job = {"source": "manual"}
    cfg = SymbolConfig(
        symbol="JPN225", magic=1, enabled=True,
        strategy="burst", timeframe="M30",
        sl_atr_mult=0.7, trail_start_atr=0.3,
        opt_updated_at=1.0,
        opt_summary={"holdout": {"net_r": 146.7, "score": 126.0,
                                 "profit_factor": 1.6, "trades": 358},
                     "validated": True},
    )
    store = MagicMock()
    store.symbols = {"JPN225": cfg}
    store.system = SystemConfig(charge_costs=True)
    store.opt_params.return_value = {"min_positive_ratio": 0.7}
    store.get_setting.return_value = {}
    store.record_opt_run = MagicMock()
    opt.store = store
    opt.client = MagicMock()
    opt.client.positions.return_value = []
    opt.entry_lock = None
    opt._incumbent_guard_holdout = lambda c: {
        "net_r": 146.7, "score": 126.0, "profit_factor": 1.6, "trades": 358,
    }
    opt._incumbent_kept_tail = lambda c: " (damga +146.7R)"
    plan = {
        "cfg": cfg,
        "started": 0.0,
        "error": None,
        "attempts": [
            {
                "ok": True, "validated": True, "order": 0,
                "timeframe": "M30", "strategy": "burst",
                "best": {
                    "score": 21.0,
                    "positive_ratio": 0.33,
                    "selection_positive_ratio": 1.0,
                    "min_positive_ratio": 0.7,
                    "params": {},
                    "validation": {"net_r": 10.0, "score": 8.0},
                    "holdout": {"net_r": 12.0, "score": 9.0, "trades": 40},
                    "selection": {"net_r": 20.0, "score": 15.0},
                },
            },
            {
                "ok": True, "validated": True, "order": 1,
                "timeframe": "M15", "strategy": "burst",
                "best": {
                    "score": 18.0,
                    "positive_ratio": 0.5,
                    "selection_positive_ratio": 1.0,
                    "min_positive_ratio": 0.7,
                    "params": {},
                    "validation": {"net_r": 8.0, "score": 6.0},
                    "holdout": {"net_r": 9.0, "score": 7.0, "trades": 30},
                    "selection": {"net_r": 15.0, "score": 12.0},
                },
            },
        ],
    }
    report = opt._finish_symbol(plan, apply_best=True)
    assert report.get("applied") is False
    reason = str(report.get("keep_reason") or "")
    assert "F6" in reason, reason
    assert "0.33" in reason or "pr=" in reason, reason
    store.record_opt_run.assert_called()
