"""edge_scale rewards a short holdout window, not a better edge.

``_edge_metric`` is holdout net R / holdout_days. Bar cap is fixed, so M5
sees ~92 days and M30 sees ~610. The same total R therefore looks six times
more productive on M5, and the square-root median ratio pushes that symbol
toward EDGE_MAX.

This test is the proof, not the fix. The metric stays until the replacement
is chosen; EDGE_MIN/MAX and risk_percent are untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

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


def _cfg(symbol: str, *, days: float, net_r: float) -> SymbolConfig:
    c = SymbolConfig(symbol=symbol, magic=abs(hash(symbol)) % 10_000)
    c.enabled = True
    c.opt_summary = {
        "holdout_days": days,
        "holdout": {"net_r": net_r, "expectancy": 0.15, "trades": 200,
                    "max_dd_r": 20.0},
    }
    return c


def _rm(*cfgs: SymbolConfig) -> RiskManager:
    return RiskManager(_Store(cfgs), _Client())


# Same GER40-shaped total on the two windows the live book actually carries.
SAME_R = 180.2
M5_DAYS = 91.8
M30_DAYS = 638.1


def test_the_same_holdout_r_looks_larger_on_a_shorter_window():
    """Identical net R, M5-length vs M30-length window.

    Fail-first (equality) without any metric change:

        AssertionError: same net R, different window: M5-days scale 1.808 vs
        M30-days scale 0.686

    The metric is not replaced here. This assertion records the split so a
    later candidate can be scored against it.
    """
    short = _cfg("SHORT", days=M5_DAYS, net_r=SAME_R)
    long = _cfg("LONG", days=M30_DAYS, net_r=SAME_R)
    mid = _cfg("MID", days=300.0, net_r=SAME_R)
    rm = _rm(short, long, mid)
    short_s = rm.edge_scale(short)
    long_s = rm.edge_scale(long)
    assert short_s > long_s
    # sqrt(days_long / days_short) ≈ 2.636, matching 1.808 / 0.686.
    assert short_s / long_s == pytest.approx((M30_DAYS / M5_DAYS) ** 0.5, rel=1e-6)
    assert short_s == pytest.approx(1.808, abs=0.001)
    assert long_s == pytest.approx(0.686, abs=0.001)
