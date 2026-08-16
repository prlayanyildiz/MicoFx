"""Same holdout R on two window lengths must get the same edge_scale.

LEV-1: ``_edge_metric`` was net R / holdout_days, so M5 (~92d) looked six
times more productive than M30 (~610d) with identical totals. The replacement
is holdout net R / holdout max_dd_r — both sides of the ratio come from the
same slice, so window length cancels. sqrt and EDGE_MIN/MAX stay.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager


class _Store:
    def __init__(self, symbols):
        self.symbols = {c.symbol: c for c in symbols}
        self.system = SystemConfig()
        self.system.size_by_edge = True

    def get_setting(self, key, default=None):
        return default


class _Client:
    pass


def _cfg(symbol: str, *, days: float = 100.0, net_r: float = 180.2,
         max_dd_r: float | None = 20.0, enabled: bool = True) -> SymbolConfig:
    c = SymbolConfig(symbol=symbol, magic=abs(hash(symbol)) % 10_000)
    c.enabled = enabled
    hold = {"net_r": net_r, "expectancy": 0.15, "trades": 200}
    if max_dd_r is not None:
        hold["max_dd_r"] = max_dd_r
    c.opt_summary = {"holdout_days": days, "holdout": hold}
    return c


def _rm(*cfgs: SymbolConfig) -> RiskManager:
    return RiskManager(_Store(cfgs), _Client())


SAME_R = 180.2
M5_DAYS = 91.8
M30_DAYS = 638.1
SAME_DD = 20.0


def test_the_same_holdout_r_is_the_same_edge_on_two_timeframes():
    """Identical net R and maxDD; only holdout_days differs."""
    short = _cfg("SHORT", days=M5_DAYS, net_r=SAME_R, max_dd_r=SAME_DD)
    long = _cfg("LONG", days=M30_DAYS, net_r=SAME_R, max_dd_r=SAME_DD)
    mid = _cfg("MID", days=300.0, net_r=SAME_R, max_dd_r=SAME_DD)
    rm = _rm(short, long, mid)
    assert rm.edge_scale(short) == rm.edge_scale(long), (
        f"same net R, different window: "
        f"M5-days scale {rm.edge_scale(short):.3f} vs "
        f"M30-days scale {rm.edge_scale(long):.3f}")
    assert rm.edge_scale(short) == 1.0  # three identical ratios → median match


def test_a_missing_or_non_positive_drawdown_is_neutral_not_the_floor():
    peers = [
        _cfg("A", net_r=40.0, max_dd_r=20.0),
        _cfg("B", net_r=80.0, max_dd_r=20.0),
        _cfg("C", net_r=120.0, max_dd_r=20.0),
    ]
    missing = _cfg("MISS", net_r=180.2, max_dd_r=None)
    zero = _cfg("ZERO", net_r=180.2, max_dd_r=0.0)
    neg_dd = _cfg("NEGDD", net_r=180.2, max_dd_r=-5.0)
    neg_r = _cfg("NEGR", net_r=-10.0, max_dd_r=20.0)
    rm = _rm(*peers, missing, zero, neg_dd, neg_r)
    for cfg in (missing, zero, neg_dd, neg_r):
        assert rm.edge_scale(cfg) == 1.0, cfg.symbol
    # Peers still size against each other; a hole does not collapse the book.
    assert rm.edge_scale(peers[0]) != 1.0 or rm.edge_scale(peers[2]) != 1.0


def test_fewer_than_three_positive_metrics_stay_neutral():
    a = _cfg("A", net_r=40.0, max_dd_r=10.0)
    b = _cfg("B", net_r=400.0, max_dd_r=10.0)
    assert _rm(a, b).edge_scale(a) == 1.0
    assert _rm(a, b).edge_scale(b) == 1.0
