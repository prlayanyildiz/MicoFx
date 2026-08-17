"""A charge_costs=True stamp cannot sit next to cost_per_trade_r=0.

AV1: JPN225, SpotBrent, UK100, XAUUSD live stamps say charge_costs=True
while holdout.cost_per_trade_r is 0.0000, with trades. MT5 history on
those four has no zero-spread bars, so this is not missing quotes.

The remaining writer: apply() still falls back to store.system.charge_costs
when detail omits the key (panel apply from opt_history, which
record_opt_run never stored charge_costs). Store is True; holdout is the
cost-free sweep. Same lie as the 14.08 20:17 SpotBrent row, one door over.

Found on the AV1 live-account pull (2026-08-16). Explicit True + trades +
zero cost must refuse; an omitted key with zero cost must stamp False.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, cfg):
        self._cfg = cfg
        self.symbols = {cfg.symbol: cfg}
        self.system = SystemConfig(charge_costs=True)

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch, source=""):
        for k, v in patch.items():
            if v is not None:
                setattr(self._cfg, k, v)
        return self._cfg


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []


def _cfg():
    return SymbolConfig(symbol="XAUUSD", magic=1, strategy="t3_stoch",
                        timeframe="M5", sl_atr_mult=1.0, trail_step_atr=0.6)


def _detail(**over):
    d = {
        "holdout": {"trades": 400, "expectancy": 0.10, "net_r": 40.0,
                    "cost_per_trade_r": 0.0, "profit_factor": 1.2, "score": 8.0},
        "validation": {"trades": 200, "expectancy": 0.08, "net_r": 16.0,
                       "profit_factor": 1.2, "score": 7.0},
        "selection": {"trades": 800, "expectancy": 0.09, "profit_factor": 1.3},
        "positive_ratio": 0.8,
        "holdout_days": 40.0,
        "validated": True,
    }
    d.update(over)
    return d


def _opt(cfg):
    opt = Optimizer(store=_Store(cfg), client=_Client())
    opt._holdout_costed = lambda *a, **k: None
    return opt


def test_explicit_charged_stamp_with_zero_cost_is_refused():
    cfg = _cfg()
    result = _opt(cfg).apply(
        "XAUUSD", {"sl_atr_mult": 1.2}, score=9.9,
        detail=_detail(charge_costs=True), timeframe="M5", strategy="t3_stoch")
    assert not result["ok"]
    assert "maliyet" in (result.get("error") or "").lower()
    assert cfg.opt_score != 9.9


def test_omitted_stamp_with_zero_cost_does_not_claim_charged():
    cfg = _cfg()
    result = _opt(cfg).apply(
        "XAUUSD", {"sl_atr_mult": 1.2}, score=9.9,
        detail=_detail(), timeframe="M5", strategy="t3_stoch")
    assert result["ok"], result
    assert cfg.opt_summary["charge_costs"] is False
    assert cfg.opt_summary["holdout"]["cost_per_trade_r"] == 0.0


def test_charged_stamp_with_real_cost_still_writes():
    cfg = _cfg()
    detail = _detail(charge_costs=True)
    detail["holdout"] = {**detail["holdout"], "cost_per_trade_r": 0.027}
    result = _opt(cfg).apply(
        "XAUUSD", {"sl_atr_mult": 1.2}, score=9.9,
        detail=detail, timeframe="M5", strategy="t3_stoch")
    assert result["ok"], result
    assert cfg.opt_summary["charge_costs"] is True
