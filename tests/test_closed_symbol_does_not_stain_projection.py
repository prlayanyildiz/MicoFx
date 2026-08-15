"""A disabled symbol's costed_negative flag still painted the book red.
Found 16.08: operator closed UK100/SpotBrent/JPN225; the panel warning
stayed because risk.py read the flag before ``row is None``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager


class _Client:
    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 100.0, "point": 0.01}

    def resolve(self, symbol):
        return symbol

    def money_per_price_unit(self, symbol, lot):
        return 10.0 * lot

    def min_stop_distance(self, symbol):
        return 0.0

    def normalize_volume(self, symbol, lot):
        return round(lot, 2)

    def margin_for(self, symbol, lot, side):
        return 10.0

    def tick(self, symbol):
        return {"bid": 100.0, "ask": 100.1, "spread": 0.1}


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = SystemConfig()
        self.system.size_by_edge = False


def _cfg(symbol, *, enabled, costed_negative, magic):
    cfg = SymbolConfig(symbol=symbol, magic=magic, enabled=enabled,
                       lot_mode="fixed", fixed_lot=0.1, sl_atr_mult=1.0)
    cfg.opt_summary = {
        "holdout": {"expectancy": 0.1, "net_r": 10.0},
        "holdout_days": 20.0,
        "holdout_costed": {"net_r": -4.0, "expectancy": -0.04},
        "charge_costs": True,
        "costed_negative": costed_negative,
    }
    return cfg


def _cap(*cfgs):
    rm = RiskManager.__new__(RiskManager)
    rm.store = _Store(cfgs)
    rm.client = _Client()
    return rm.capacity([], {"equity": 2000.0, "balance": 2000.0,
                            "margin_free": 1800.0, "margin": 0.0},
                       atr_by_symbol={c.symbol: 1.0 for c in cfgs})


def test_closed_costed_negative_symbol_does_not_flag_the_book():
    out = _cap(_cfg("UK100", enabled=False, costed_negative=True, magic=1),
               _cfg("GER40", enabled=True, costed_negative=False, magic=2))
    assert out["projected_costed_negative"] is False


def test_open_costed_negative_symbol_still_flags_the_book():
    out = _cap(_cfg("UK100", enabled=True, costed_negative=True, magic=1))
    assert out["projected_costed_negative"] is True
