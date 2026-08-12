"""An apply that carries no evidence must not leave the previous evidence standing.

``Optimizer.apply`` writes the strategy, the timeframe, the parameters, the
score and the timestamp unconditionally, but writes ``opt_summary`` only
``if detail:``. Applying without a detail block therefore changes what trades
while leaving behind a summary measured on the configuration that no longer
exists.

The summary is not decoration. Three separate consumers read it as the record
of what this configuration proved:

  * ``/api/analysis/portfolio-gates`` takes ``holdout.trades``,
    ``holdout.expectancy`` and ``holdout.cost_per_trade_r`` straight out of it
    to decide measurability, the cost gate and which review layer the symbol
    lands in - the panel the hourly review reads before cutting a symbol.
  * ``risk._edge_metric`` sizes the position from ``holdout.net_r`` over
    ``holdout_days``.
  * ``_beats_incumbent`` compares the next candidate's score against
    ``holdout``, and its spread assumption against ``spread_scale``.

All three would be reading numbers earned by different parameters, on a
different strategy, possibly on a different timeframe - and reading them as
current, because nothing in the row says otherwise.

Reachable from the panel: the results-table apply posts params without a
run_id, and ``detail is None`` on that path is explicitly documented in
web/app.py as indistinguishable from a hand-typed apply. It happened today -
EURUSD was applied flow_rev/H1 at 11:26:58, fifteen seconds after the
auto-apply gate had refused the same candidate, and its opt_summary is empty.
Empty is the visible half of this: the symbol had no earlier summary to keep.
A symbol that has one keeps it, which is the half that misleads.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, cfg):
        self._cfg = cfg
        self.symbols = {cfg.symbol: cfg}
        self.updated_with = None

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch):
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
    "holdout": {"trades": 300, "expectancy": 0.31, "net_r": 92.0,
                "cost_per_trade_r": 0.04},
    "holdout_days": 120.0,
    "params": {"sl_atr_mult": 1.0, "trail_step_atr": 0.6},
    "spread_scale": 1.05,
}


def _cfg() -> SymbolConfig:
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, strategy="t3_stoch",
                       timeframe="M15", sl_atr_mult=1.0, trail_step_atr=0.6)
    cfg.opt_summary = dict(EARLIER)
    return cfg


def _apply(**kw):
    cfg = _cfg()
    store = _Store(cfg)
    opt = Optimizer(store=store, client=_Client())
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, **kw)
    assert result["ok"] is True, result
    return cfg


# ------------------------------------------------------- the defect

def test_a_summary_measured_on_other_parameters_is_not_kept():
    cfg = _apply()
    assert cfg.sl_atr_mult == 2.4, "yeni parametre yazilmis olmali"
    summary = cfg.opt_summary or {}
    kept = (summary.get("params") or {}).get("sl_atr_mult")
    assert kept != 1.0, (
        "damga hala eski parametreye ait: konfig 2.4 ile isliyor, "
        "ozet 1.0 ile olculmus")


def test_the_gate_panel_does_not_read_a_stale_holdout():
    """portfolio-gates takes trades/expectancy/cost straight from here."""
    hold = (_apply().opt_summary or {}).get("holdout") or {}
    assert hold.get("expectancy") != 0.31, (
        "kapi paneli baska parametrelerle kazanilmis 0.31R'yi guncel saniyor")


def test_the_spread_stamp_does_not_outlive_its_configuration():
    """_beats_incumbent compares the next candidate against this assumption."""
    assert (_apply().opt_summary or {}).get("spread_scale") != 1.05


def test_a_family_swap_does_not_keep_the_previous_families_record():
    cfg = _apply(strategy="burst", timeframe="M5")
    assert cfg.strategy == "burst" and cfg.timeframe == "M5"
    hold = (cfg.opt_summary or {}).get("holdout") or {}
    assert hold.get("trades") != 300, (
        "burst/M5 calisiyor ama ozet t3_stoch/M15'in 300 islemini gosteriyor")


# --------------------------------------------- what must keep working

def test_an_apply_with_evidence_records_it():
    cfg = _cfg()
    store = _Store(cfg)
    opt = Optimizer(store=store, client=_Client())
    detail = {"holdout": {"trades": 44, "expectancy": 0.2, "net_r": 8.8},
              "validation": {}, "selection": {}, "holdout_days": 30.0,
              "positive_ratio": 1.0}
    assert opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=detail)["ok"]
    hold = (cfg.opt_summary or {}).get("holdout") or {}
    assert hold.get("trades") == 44
    assert (cfg.opt_summary or {}).get("holdout_days") == 30.0
    assert "spread_scale" in (cfg.opt_summary or {})


def test_the_configuration_itself_is_still_applied():
    """Only the stale record goes; the apply keeps working."""
    cfg = _apply(strategy="burst", timeframe="M5")
    assert cfg.sl_atr_mult == 2.4
    assert cfg.strategy == "burst"
    assert cfg.timeframe == "M5"
    assert cfg.opt_score == 9.9
