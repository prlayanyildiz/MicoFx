"""Do not stamp holdout_costed when the charged replay is too thin.

US30 revert applied a solid n=276 paper holdout, then apply() overlaid
holdout_costed n=17 — holdout_expectancy preferred the noise until MIN_COSTED_N.
Refuse to write (and strip on load) costed stamps below that floor.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.store as store_module
from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer
from micofx.store import Store
from micofx.supervisor import Supervisor


def test_apply_skips_thin_holdout_costed_stamp():
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = False
    cfg = SymbolConfig(
        symbol="US30", magic=1, enabled=True,
        strategy="channel_break", timeframe="M30",
        sl_atr_mult=2.5, trail_start_atr=0.8,
        opt_updated_at=1.0,
        opt_summary={
            "holdout": {"net_r": 43.0, "trades": 276, "expectancy": 0.156},
            "holdout_costed": {
                "net_r": 1.68, "trades": 17, "expectancy": 0.099,
            },
            "validated": True,
        },
    )
    store = MagicMock()
    store.symbols = {"US30": cfg}
    store.system = SystemConfig(charge_costs=True)
    store.opt_params.return_value = {"min_positive_ratio": 0.7}
    store.get_setting.return_value = {"reopt_min_age_hours": 0}
    written = {}

    def _upd(sym, patch, source=""):
        written.clear()
        written.update(patch)
        return cfg

    store.update_symbol = MagicMock(side_effect=_upd)
    opt.store = store
    opt.client = MagicMock()
    opt.client.connected = True
    opt.client.positions.return_value = []
    opt.entry_lock = None
    opt._spread_scale = lambda s: 1.0
    opt._holdout_costed = lambda *a, **k: {
        "trades": 17, "net_r": 1.68, "expectancy": 0.099, "score": 0.3,
        "profit_factor": 1.2, "cost_per_trade_r": 0.006, "cost_r": 0.11,
        "wins": 6, "losses": 11, "win_rate": 35.0, "max_dd_r": 3.0,
        "capture": 0.1, "exits": {},
    }
    detail = {
        "holdout": {
            "net_r": 43.0, "trades": 276, "expectancy": 0.156,
            "profit_factor": 1.37, "cost_per_trade_r": 0.0,
        },
        "validation": {
            "net_r": 26.0, "trades": 300, "expectancy": 0.09,
            "profit_factor": 1.2,
        },
        "selection": {"net_r": 77.0, "trades": 700},
        "holdout_days": 90.0,
        "validated": True,
        "positive_ratio": 1.0,
        "min_positive_ratio": 0.7,
        "charge_costs": False,
    }
    res = opt.apply(
        "US30",
        {"sl_atr_mult": 2.5, "trail_start_atr": 0.8, "trail_step_atr": 2.2,
         "max_spread_atr": 0.05},
        score=17.0,
        detail=detail,
        timeframe="M30",
        strategy="channel_break",
    )
    assert res.get("ok") is True, res
    summary = written.get("opt_summary") or {}
    costed = summary.get("holdout_costed")
    assert costed is None or int((costed or {}).get("trades") or 0) == 0


def test_load_strips_thin_holdout_costed(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    st = Store()
    fat = {
        "symbol": "TESTTHIN",
        "magic": 919192,
        "enabled": True,
        "strategy": "channel_break",
        "timeframe": "M30",
        "sl_atr_mult": 2.5,
        "opt_summary": {
            "holdout": {"net_r": 43.0, "trades": 276, "expectancy": 0.156},
            "holdout_costed": {
                "net_r": 1.68, "trades": 17, "expectancy": 0.099,
            },
            "validated": True,
        },
    }
    with st._lock:
        st._db.execute(
            "INSERT INTO symbols(symbol, position, payload) VALUES(?,?,?)",
            ("TESTTHIN", 99, json.dumps(fat)),
        )
        st._db.commit()
    st._load_symbols()
    cfg = st.symbols["TESTTHIN"]
    costed = (cfg.opt_summary or {}).get("holdout_costed")
    assert not costed or int(costed.get("trades") or 0) < 1
    assert Supervisor.holdout_expectancy(cfg) == 0.156
