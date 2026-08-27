"""apply() must copy walk-forward ``validated`` onto the live symbol row.

The flag is already on every opt_runs payload (262/262). SymbolConfig had
no field and apply() wrote opt_summary without it, so the book snapshot
read None for all ten symbols. Universe scan (DEVAM §7) will rank 1729
names and mark validated; if the flag never reaches the row, that output
cannot be used.

Old rows stay None: missing is not False.
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


def _opt(cfg):
    opt = Optimizer(store=_Store(cfg), client=_Client())
    opt._holdout_costed = lambda *a, **k: None
    return opt


def _detail(validated):
    return {
        "holdout": {"trades": 80, "expectancy": 0.2, "net_r": 16.0,
                    "cost_per_trade_r": 0.04, "profit_factor": 1.3, "score": 8.0},
        "validation": {"trades": 80, "expectancy": 0.2, "net_r": 16.0,
                       "profit_factor": 1.3, "score": 8.0},
        "selection": {"trades": 80, "expectancy": 0.2, "profit_factor": 1.3},
        "positive_ratio": 0.8,
        "holdout_days": 40.0,
        "validated": validated,
        "spread_scale": 1.0,
        "charge_costs": True,
        "min_positive_ratio": 0.6,
    }


def test_apply_copies_validated_true_onto_the_symbol():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, strategy="stoch_flip", timeframe="M15")
    assert cfg.validated is None
    opt = _opt(cfg)
    opt.apply("XAUUSD", {"sl_atr_mult": 1.5}, score=9.0,
              detail=_detail(True), timeframe="M15", strategy="stoch_flip")
    assert cfg.validated is True
    assert cfg.opt_summary.get("validated") is True


def test_apply_copies_validated_false_and_that_is_not_none():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, strategy="stoch_flip", timeframe="M15")
    opt = _opt(cfg)
    opt.apply("XAUUSD", {"sl_atr_mult": 1.5}, score=9.0,
              detail=_detail(False), timeframe="M15", strategy="stoch_flip")
    assert cfg.validated is False
    assert cfg.opt_summary.get("validated") is False


def test_a_row_that_never_had_the_key_loads_as_none_not_false():
    cfg = SymbolConfig.from_dict({"symbol": "GER40", "magic": 2})
    assert cfg.validated is None
    again = SymbolConfig.from_dict({**cfg.to_dict(), "validated": None})
    assert again.validated is None
    false = SymbolConfig.from_dict({**cfg.to_dict(), "validated": False})
    assert false.validated is False
