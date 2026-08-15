"""Cost-free search can pick a config live will pay for and lose on.

O2: FRA40 paper +0.049, same slice charged -0.056. Apply still happens
(#50), but the charged holdout has to be stamped so the next pass can
count how many symbols are in that state.
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


def _cfg() -> SymbolConfig:
    return SymbolConfig(symbol="FRA40", magic=1, strategy="t3_stoch",
                        timeframe="M15", sl_atr_mult=1.0, trail_step_atr=0.6)


def _detail(paper_e=0.049):
    return {
        "holdout": {"trades": 665, "expectancy": paper_e, "net_r": 32.0,
                    "cost_per_trade_r": 0.0, "profit_factor": 1.2, "score": 8.0},
        "validation": {"trades": 400, "expectancy": 0.06, "net_r": 20.0,
                       "profit_factor": 1.2, "score": 7.0},
        "selection": {"trades": 800, "expectancy": 0.07, "profit_factor": 1.3},
        "positive_ratio": 0.8,
        "holdout_days": 40.0,
        "charge_costs": False,
    }


def _apply(costed, logs=None):
    cfg = _cfg()
    store = _Store(cfg)
    opt = Optimizer(store=store, client=_Client())
    opt._holdout_costed = lambda *a, **k: costed
    if logs is not None:
        from micofx.logbus import LOG
        orig = LOG.emit

        def _cap(msg, level="INFO", symbol=""):
            logs.append((msg, level, symbol))
            return orig(msg, level, symbol)

        LOG.emit = _cap
    try:
        result = opt.apply("FRA40", {"sl_atr_mult": 2.4}, score=9.9,
                           detail=_detail(), timeframe="M15", strategy="t3_stoch")
    finally:
        if logs is not None:
            LOG.emit = orig
    assert result["ok"] is True, result
    return cfg


def test_negative_costed_holdout_flags_and_logs_but_still_applies():
    logs = []
    cfg = _apply({"trades": 665, "expectancy": -0.056}, logs)
    summary = cfg.opt_summary
    assert cfg.sl_atr_mult == 2.4, "apply reddedilmemeli"
    assert summary["charge_costs"] is False, "arama rejimi karismamali"
    assert summary["holdout_costed"]["expectancy"] == -0.056
    assert summary["costed_negative"] is True
    assert any(
        "FRA40" in m and "maliyetsiz" in m and "maliyetli ayni dilim" in m
        and level == "OPT"
        for m, level, _ in logs
    ), logs


def test_positive_costed_holdout_is_stamped_without_the_flag():
    cfg = _apply({"trades": 200, "expectancy": 0.12})
    summary = cfg.opt_summary
    assert summary["holdout_costed"]["expectancy"] == 0.12
    assert "costed_negative" not in summary
    assert summary["charge_costs"] is False


def test_missing_costed_eval_does_not_break_apply_or_invent_a_flag():
    cfg = _apply(None)
    summary = cfg.opt_summary
    assert cfg.sl_atr_mult == 2.4
    assert "holdout_costed" not in summary
    assert "costed_negative" not in summary
    assert summary["charge_costs"] is False


def test_a_broken_costed_eval_leaves_apply_intact():
    cfg = _cfg()
    store = _Store(cfg)
    opt = Optimizer(store=store, client=_Client())

    def _boom(*a, **k):
        raise RuntimeError("terminal gitti")

    opt._holdout_costed = _boom
    result = opt.apply("FRA40", {"sl_atr_mult": 2.4}, score=9.9,
                       detail=_detail(), timeframe="M15", strategy="t3_stoch")
    assert result["ok"] is True
    assert "holdout_costed" not in cfg.opt_summary
    assert "costed_negative" not in cfg.opt_summary


def test_the_charged_slice_is_the_one_the_sweep_used():
    """The log line names a paper number and a charged one as "the same slice".

    It was fetching a fixed 8000 bars and cutting them five ways, while the
    sweep runs on opt_params' max_bars (99000 live). The last fifth of 8000
    bars is not the last fifth of 99000, so the two expectancies described
    different periods and the comparison was false in exactly the way the
    charge_costs stamp exists to prevent.
    """
    import inspect

    from micofx.optimizer import Optimizer

    src = inspect.getsource(Optimizer._holdout_costed)
    helper = inspect.getsource(Optimizer._bars_for_holdout)
    assert 'opt.get("max_bars")' in helper, "fallback bar count must come from the sweep's params"
    assert 'opt.get("segments")' in src, "so must the segment count"
    assert "_bars_for_holdout" in src, "must reuse the run snapshot when it exists"
    assert "self.client.bars(symbol, timeframe, want)" in helper, (
        "a hardcoded window would make the comparison false")


def test_spread_scale_on_the_row_is_the_sweeps_not_the_live_clock():
    cfg = _cfg()
    store = _Store(cfg)
    opt = Optimizer(store=store, client=_Client())
    opt._holdout_costed = lambda *a, **k: None
    opt._spread_scale = lambda symbol: 9.0
    result = opt.apply(
        "FRA40", {"sl_atr_mult": 2.4}, score=9.9,
        detail={**_detail(), "spread_scale": 0.41},
        timeframe="M15", strategy="t3_stoch")
    assert result["ok"] is True, result
    assert cfg.opt_summary["spread_scale"] == 0.41
    assert cfg.opt_summary["charge_costs"] is False
