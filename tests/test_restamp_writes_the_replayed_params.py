"""STAMP-1a: restamping holdout must write the params the replay ran.

GAP-5 refreshed ``opt_summary.holdout`` and left ``params`` on the previous
apply (NAS100 trail 0.8/2.2). Live — and the replay — was 1.0/1.8. The stamp
then claimed a config it had not measured.

``detail['params']`` is the leftover. The live row is what was simulated.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer
from micofx.strategy import stamp_fields


class _Store:
    def __init__(self, cfg):
        self._cfg = cfg
        self.symbols = {cfg.symbol: cfg}
        self.updated_with = None
        self.source = None

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch, source=""):
        self.updated_with = patch
        self.source = source
        for k, v in patch.items():
            if v is not None:
                setattr(self._cfg, k, v)
        return self._cfg


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []


REPLAY = {
    "holdout": {"trades": 1040, "expectancy": 0.10, "net_r": 107.19,
                "max_dd_r": 40.0, "cost_per_trade_r": 0.03},
    "holdout_days": 90.0,
    "validated": True,
    # Leftover from the previous apply — must not win.
    "params": {"trail_start_atr": 0.8, "trail_step_atr": 2.2},
}


def _cfg() -> SymbolConfig:
    cfg = SymbolConfig(symbol="NAS100", magic=1, strategy="mtf_pullback",
                       timeframe="M30", sl_atr_mult=1.0,
                       trail_start_atr=1.0, trail_step_atr=1.8)
    cfg.opt_summary = {
        "holdout": {"trades": 800, "net_r": 50.0},
        "holdout_days": 80.0,
        "validated": True,
        "params": {"trail_start_atr": 0.8, "trail_step_atr": 2.2,
                   "sl_atr_mult": 1.0},
    }
    return cfg


def _opt():
    cfg = _cfg()
    store = _Store(cfg)
    return Optimizer(store=store, client=_Client()), store, cfg


def test_restamp_writes_live_params_not_the_leftover_apply():
    opt, store, cfg = _opt()
    result = opt.restamp_from_replay("NAS100", REPLAY, source="GAP-5 replay")
    assert result["ok"] is True, result
    stamped = (cfg.opt_summary or {}).get("params") or {}
    assert stamped["trail_start_atr"] == 1.0
    assert stamped["trail_step_atr"] == 1.8
    assert stamped["sl_atr_mult"] == 1.0
    assert (cfg.opt_summary or {}).get("holdout", {}).get("net_r") == 107.19
    assert (cfg.opt_summary or {}).get("stamp_source") == "GAP-5 replay"
    # Live row is not an apply. Exit fields already matched the replay.
    assert cfg.trail_start_atr == 1.0
    assert cfg.trail_step_atr == 1.8


def test_restamp_omits_fields_the_family_does_not_read():
    """stoch_flip does not read htf_factor/adx_min; stamping them is noise."""
    cfg = SymbolConfig(symbol="GER40", magic=1, strategy="stoch_flip",
                       timeframe="M30", htf_factor=9, adx_min=15.0,
                       sl_atr_mult=1.2)
    cfg.opt_summary = {"params": {"htf_factor": 9, "adx_min": 15.0}}
    store = _Store(cfg)
    opt = Optimizer(store=store, client=_Client())
    result = opt.restamp_from_replay("GER40", REPLAY, source="test")
    assert result["ok"] is True, result
    stamped = (cfg.opt_summary or {}).get("params") or {}
    allow = stamp_fields("stoch_flip")
    assert "htf_factor" not in allow
    assert "adx_min" not in allow
    assert "htf_factor" not in stamped
    assert "adx_min" not in stamped
    assert "sl_atr_mult" in stamped



def test_restamp_without_holdout_is_refused_and_the_stamp_does_not_move():
    opt, store, cfg = _opt()
    detail = {k: v for k, v in REPLAY.items() if k != "holdout"}
    result = opt.restamp_from_replay("NAS100", detail)
    assert result["ok"] is False, result
    assert "holdout" in (result.get("error") or "")
    assert store.updated_with is None
    assert (cfg.opt_summary or {}).get("params", {}).get("trail_start_atr") == 0.8
    assert (cfg.opt_summary or {}).get("holdout", {}).get("net_r") == 50.0
