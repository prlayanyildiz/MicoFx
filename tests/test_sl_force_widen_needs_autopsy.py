"""Force SL widen needs autopsy premature evidence + charged non-regression.

Charged-alone still flattered 0.5 stops; autopsy-alone wants 1.0 and
collapses the stamp. Morning live patch: both, or WFO with the >=0.9 floor.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import (
    Optimizer,
    premature_sl_count_from_autopsy,
)


def _premature_rows(symbol: str, n: int) -> list[dict]:
    return [
        {
            "symbol": symbol,
            "after_1h_bars": 12,
            "after_1h_through_entry": True,
            "after_1h_recovery_r": 1.2,
            "exit_reason": "sl",
            "r_realised": -1.0,
        }
        for _ in range(n)
    ]


def _opt(cfg: SymbolConfig, measured: dict, autopsies=None) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = True
    store = MagicMock()
    store.symbols = {cfg.symbol: cfg}
    store.system = SystemConfig(charge_costs=True)
    store.opt_params.return_value = {"lookback_days": 180, "segments": 5}
    store.update_symbol = MagicMock(return_value=cfg)
    store.get_setting = MagicMock(return_value=autopsies if autopsies is not None else [])
    opt.store = store
    opt.client = MagicMock()
    opt.client.connected = True
    opt.client.positions.return_value = []
    opt.entry_lock = None
    opt._spread_scale = lambda sym: 1.0
    opt._holdout_costed = lambda *a, **k: dict(measured)
    return opt


def test_premature_sl_count_counts_through_entry_or_strong_recovery():
    rows = [
        {"symbol": "NAS100", "after_1h_bars": 8,
         "after_1h_through_entry": True, "after_1h_recovery_r": 0.1},
        {"symbol": "NAS100", "after_1h_bars": 8,
         "after_1h_through_entry": False, "after_1h_recovery_r": 0.9},
        {"symbol": "NAS100", "after_1h_bars": 8,
         "after_1h_through_entry": False, "after_1h_recovery_r": 0.2},
        {"symbol": "XAUUSD", "after_1h_bars": 8,
         "after_1h_through_entry": True, "after_1h_recovery_r": 2.0},
        {"symbol": "NAS100", "after_1h_bars": 0,
         "after_1h_through_entry": True, "after_1h_recovery_r": 2.0},
    ]
    assert premature_sl_count_from_autopsy(rows, "NAS100") == 2
    assert premature_sl_count_from_autopsy(rows, "XAUUSD") == 1
    assert premature_sl_count_from_autopsy(rows, "US30") == 0


def test_force_sl_widen_refuses_without_autopsy_even_if_charged_up():
    cfg = SymbolConfig(
        symbol="NAS100", magic=1, enabled=True,
        strategy="mtf_pullback", timeframe="M30",
        sl_atr_mult=0.5, trail_start_atr=0.3, trail_step_atr=2.5,
        blocked_entry_hours=[],
        opt_summary={"holdout": {"net_r": 100.0, "trades": 700, "score": 60.0},
                     "holdout_days": 500.0, "validated": True},
    )
    opt = _opt(cfg, {
        "trades": 500, "net_r": 105.0, "expectancy": 0.21, "score": 62.0,
        "profit_factor": 1.2, "cost_per_trade_r": 0.03, "cost_r": 15.0,
        "wins": 200, "losses": 300, "win_rate": 40.0, "max_dd_r": 40.0,
        "capture": 0.1, "exits": {}, "holdout_days": 500.0,
    }, autopsies=[])
    res = opt.apply(
        "NAS100", {"sl_atr_mult": 1.0},
        score=0.0, detail=None, timeframe="M30", strategy="mtf_pullback",
    )
    assert res.get("ok") is False
    assert "otopsi" in (res.get("error") or "").lower()
    opt.store.update_symbol.assert_not_called()


def test_force_sl_widen_lands_with_autopsy_and_charged_up():
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
    }, autopsies=_premature_rows("GER40", 5))
    res = opt.apply(
        "GER40", {"sl_atr_mult": 1.5, "adx_min": 15.0},
        score=0.0, detail=None, timeframe="M30", strategy="channel_break",
    )
    assert res.get("ok") is True, res
