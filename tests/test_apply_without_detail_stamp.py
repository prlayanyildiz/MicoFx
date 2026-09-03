"""An apply that carries no evidence must not change what trades.

``Optimizer.apply`` used to write strategy, timeframe, params, score and
timestamp unconditionally, and write ``opt_summary`` only ``if detail:``.
Applying without a detail block therefore changed the live configuration
while leaving behind a summary measured on what no longer trades.

The summary is not decoration. Three consumers read it as current:

  * ``/api/analysis/portfolio-gates`` takes ``holdout.trades``,
    ``holdout.expectancy`` and ``holdout.cost_per_trade_r`` straight out of it.
  * ``risk._edge_metric`` sizes the position from ``holdout.net_r`` over
    ``holdout.max_dd_r`` — never from ``holdout_costed``.
  * ``_beats_incumbent`` compares the next candidate's score against
    ``holdout``, and its spread assumption against ``spread_scale``.

NAS100 traded ``mtf_pullback`` sized as ``t3_flip`` because a family swap
with overlapping OPT_FIELDS (sl/trail) looked like "same params" and kept
the previous family's holdout. Voiding the summary when recorded params
disagreed was not enough: strategy/timeframe are not in those params.

GAP-4: unstamped apply is refused. The row does not move. A complete stamp
(holdout, validated, holdout_days) is written from the applied config's
search output, including on a family swap whose OPT_FIELDS overlap.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer
from micofx.risk import RiskManager


class _Store:
    def __init__(self, cfg):
        self._cfg = cfg
        self.symbols = {cfg.symbol: cfg}
        self.updated_with = None

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch, source=""):
        self.updated_with = patch
        for k, v in patch.items():
            if v is not None:
                setattr(self._cfg, k, v)
        return self._cfg


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []


EARLIER = {
    "holdout": {"trades": 300, "expectancy": 0.31, "net_r": 60.8,
                "max_dd_r": 45.7, "cost_per_trade_r": 0.04},
    "holdout_days": 120.0,
    "validated": True,
    "params": {"sl_atr_mult": 1.0, "trail_step_atr": 0.6},
    "spread_scale": 1.05,
}

NEW = {
    "holdout": {"trades": 80, "expectancy": 0.15, "net_r": 92.0,
                "max_dd_r": 48.0, "cost_per_trade_r": 0.03, "score": 8.0},
    "validation": {"trades": 60, "expectancy": 0.12, "net_r": 7.0},
    "selection": {"trades": 200, "expectancy": 0.18},
    "holdout_days": 90.0,
    "validated": True,
    "positive_ratio": 0.8,
    "spread_scale": 1.05,
}


def _cfg() -> SymbolConfig:
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, strategy="t3_flip",
                       timeframe="M15", sl_atr_mult=1.0, trail_step_atr=0.6)
    cfg.opt_summary = dict(EARLIER)
    cfg.validated = True
    return cfg


def _opt(cfg=None):
    cfg = cfg or _cfg()
    store = _Store(cfg)
    opt = Optimizer(store=store, client=_Client())
    opt._holdout_costed = lambda *a, **k: None
    return opt, store, cfg


# ------------------------------------------------------- the defect

def test_unstamped_apply_is_refused_and_the_row_does_not_move():
    opt, store, cfg = _opt()
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9)
    assert result["ok"] is False, result
    assert "damga" in (result.get("error") or "").lower()
    assert store.updated_with is None
    assert cfg.sl_atr_mult == 1.0
    assert cfg.strategy == "t3_flip"
    assert (cfg.opt_summary or {}).get("holdout", {}).get("net_r") == 60.8


def test_apply_without_holdout_is_refused():
    opt, store, cfg = _opt()
    detail = {k: v for k, v in NEW.items() if k != "holdout"}
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=detail)
    assert result["ok"] is False, result
    assert "holdout" in (result.get("error") or "")
    assert cfg.sl_atr_mult == 1.0
    assert store.updated_with is None


def test_apply_without_holdout_days_is_refused():
    opt, store, cfg = _opt()
    detail = {k: v for k, v in NEW.items() if k != "holdout_days"}
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=detail)
    assert result["ok"] is False, result
    assert "holdout_days" in (result.get("error") or "")
    assert cfg.sl_atr_mult == 1.0


def test_apply_without_validated_is_refused():
    opt, store, cfg = _opt()
    detail = {k: v for k, v in NEW.items() if k != "validated"}
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=detail)
    assert result["ok"] is False, result
    assert "validated" in (result.get("error") or "")
    assert cfg.sl_atr_mult == 1.0
    assert cfg.validated is True


def test_family_swap_with_overlapping_opt_fields_writes_the_new_holdout():
    """NAS100: mtf_pullback applied, t3_flip 60.8R stamp kept. Overlapping sl."""
    opt, store, cfg = _opt()
    result = opt.apply(
        "XAUUSD", {"sl_atr_mult": 1.0, "trail_step_atr": 0.6}, score=9.9,
        detail=NEW, strategy="mtf_pullback", timeframe="M30")
    assert result["ok"] is True, result
    assert cfg.strategy == "mtf_pullback"
    assert cfg.timeframe == "M30"
    hold = (cfg.opt_summary or {}).get("holdout") or {}
    assert hold.get("net_r") == 92.0
    assert hold.get("trades") == 80
    assert (cfg.opt_summary or {}).get("holdout_days") == 90.0
    assert cfg.validated is True
    assert (cfg.opt_summary or {}).get("validated") is True


def test_edge_scale_prefers_thick_holdout_costed():
    """Live charging stamps paper holdout + costed overlay; size from costed."""
    cfg = _cfg()
    cfg.opt_summary = {
        "holdout": {"net_r": 10.0, "max_dd_r": 5.0, "trades": 200},
        "holdout_costed": {"net_r": 40.0, "max_dd_r": 10.0, "trades": 80},
    }
    assert RiskManager._edge_metric(cfg) == 4.0


def test_edge_scale_ignores_thin_holdout_costed():
    """US30-shaped n=17 costed noise must not rewrite the paper edge ratio."""
    cfg = _cfg()
    cfg.opt_summary = {
        "holdout": {"net_r": 10.0, "max_dd_r": 5.0, "trades": 200},
        "holdout_costed": {"net_r": 999.0, "max_dd_r": 1.0, "trades": 17},
    }
    assert RiskManager._edge_metric(cfg) == 2.0


# --------------------------------------------- what must keep working

def test_an_apply_with_evidence_records_it():
    opt, store, cfg = _opt()
    assert opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=NEW)["ok"]
    hold = (cfg.opt_summary or {}).get("holdout") or {}
    assert hold.get("trades") == 80
    assert (cfg.opt_summary or {}).get("holdout_days") == 90.0
    assert cfg.validated is True
    assert "spread_scale" in (cfg.opt_summary or {})
    assert cfg.sl_atr_mult == 2.4
