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
from micofx.optimizer import Optimizer, _holdout_span_days


def test_holdout_span_days_uses_slice_not_full_window():
    class _Bars:
        def __init__(self):
            # 600 days of hourly-ish stamps; holdout last fifth ~120d
            self.time = [float(i * 86400) for i in range(600)]

    days = _holdout_span_days(_Bars(), 480, 600)
    assert days == 119.0


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
        "holdout_days": 555.0,
    }
    opt.client.positions.return_value = []
    # This test is about where the STAMP comes from, but its patch widens
    # sl_atr_mult, so it also passes through the widen gate - which wants >=5
    # premature-stop autopsies as evidence. A MagicMock store returns a mock
    # for get_setting, not a list, so the count read 0 and the whole apply was
    # refused for a reason unrelated to what this file guards.
    store.get_setting = MagicMock(return_value=[
        {"symbol": "GER40", "exit_reason": "sl", "r_realised": -1.0,
         "after_1h_bars": 10, "after_1h_through_entry": True,
         "after_1h_recovery_r": 1.0}
        for _ in range(5)
    ])

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
    assert float((patch.get("opt_summary") or {}).get("holdout_days")) == 555.0
    # Force measure is not a WFO positive_ratio (0-1). score_consistency is
    # a different scale (Claude 03.09: JPN pr=61.7 looked like 6170%).
    assert (patch.get("opt_summary") or {}).get("positive_ratio") is None


def test_force_apply_does_not_invent_lookback_over_segments_days():
    """lookback_days=0 -> 180/5=36 used to annualize GER/JPN/NAS (Claude 03.09)."""
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = True
    cfg = SymbolConfig(
        symbol="NAS100", magic=1, enabled=True,
        strategy="mtf_pullback", timeframe="M30",
        sl_atr_mult=0.5, trail_start_atr=0.3, trail_step_atr=2.5,
    )
    store = MagicMock()
    store.symbols = {"NAS100": cfg}
    store.system = SystemConfig(charge_costs=True)
    store.opt_params.return_value = {"lookback_days": 0, "segments": 5}
    store.update_symbol = MagicMock(side_effect=lambda *a, **k: cfg)
    opt.store = store
    opt.client = MagicMock()
    opt.entry_lock = None
    opt._spread_scale = lambda sym: 1.0
    opt._holdout_costed = lambda *a, **k: {
        "trades": 740, "net_r": 100.3, "expectancy": 0.136, "score": 63.7,
        "profit_factor": 1.18, "cost_per_trade_r": 0.045, "cost_r": 33.0,
        "wins": 192, "losses": 548, "win_rate": 26.0, "max_dd_r": 57.7,
        "capture": 0.1, "exits": {},
        "holdout_days": 555.0,
    }
    opt.client.positions.return_value = []
    res = opt.apply(
        "NAS100",
        {"sl_atr_mult": 0.5, "trail_start_atr": 0.3},
        score=0.0, detail=None, timeframe="M30", strategy="mtf_pullback",
    )
    assert res.get("ok") is True, res
    days = float((store.update_symbol.call_args[0][1].get("opt_summary") or {})
                 .get("holdout_days") or 0)
    assert days == 555.0
    assert days != 36.0
