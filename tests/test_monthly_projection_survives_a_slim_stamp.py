"""Monthly projection must not go silent on a slim stamp or a zero ATR.

Live 27.08: Beklenen Aylik showed +0.00 while every symbol still had a
holdout net_r. Two holes: capacity treated a missing ``expectancy`` key as
0 and dropped the row, and a search-frozen blob with risk_per_trade=0
multiplied the rest to zero. The chip is paper holdout in dollars, not a
live P/L — blank is worse than the paper number.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_closed_symbol_does_not_stain_projection import _Client, _Store

from micofx.models import SymbolConfig
from micofx.risk import RiskManager
from micofx.supervisor import Supervisor


def _rm(cfg, atr):
    rm = RiskManager.__new__(RiskManager)
    rm.store = _Store([cfg])
    rm.client = _Client()
    return rm.capacity([], {"equity": 2000.0, "balance": 2000.0,
                            "margin_free": 1800.0, "margin": 0.0},
                       atr_by_symbol={cfg.symbol: atr})


def _slim():
    cfg = SymbolConfig(symbol="GER40", magic=1, enabled=True,
                       lot_mode="risk", risk_percent=0.8, sl_atr_mult=2.0)
    cfg.opt_summary = {
        "holdout": {"net_r": 180.4772, "n": 1294, "max_dd_r": 34.0},
        "holdout_days": 640.2,
        "holdout_costed": {"net_r": 275.95},
        "charge_costs": True,
    }
    cfg.validated = None
    return cfg


def test_holdout_expectancy_accepts_n_when_trades_is_missing():
    cfg = _slim()
    got = Supervisor.holdout_expectancy(cfg)
    assert abs(got - 180.4772 / 1294) < 1e-9


def test_a_slim_stamp_still_projects_a_monthly_dollar():
    out = _rm(_slim(), atr=36.0)
    assert out["projected_monthly"] != 0.0
    assert out["projected_costed_monthly"] != 0.0
    row = out["rows"][0]
    assert row["expectancy_r"] > 0.1


def test_zero_atr_still_projects_from_configured_risk():
    """Search-frozen capacity often has sl_dist=0; the chip must not go blank."""
    out = _rm(_slim(), atr=0.0)
    assert out["projected_monthly"] != 0.0
    # 0.8% of 2000 = 16; 180.4772 R / 640.2 d * 16 * 21 ≈ 99
    assert out["projected_monthly"] > 50


def test_missing_costed_slice_still_fills_the_headline():
    """Chip reads projected_costed_monthly; a missing costed key used to
    leave that at 0 while paper was hundreds, so the bar stayed blank."""
    cfg = _slim()
    cfg.opt_summary.pop("holdout_costed", None)
    out = _rm(cfg, atr=0.0)
    assert out["projected_costed_monthly"] != 0.0
    assert out["projected_costed_monthly"] == out["projected_monthly"]
