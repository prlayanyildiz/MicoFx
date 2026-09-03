"""Short holdout windows must not dominate the monthly projection.

GER40 36d +71.7R was 51% of a +$379/mo chip while the rest of the book
used 280-555 day stamps. Panel readout only; not an apply gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_closed_symbol_does_not_stain_projection import _Client, _Store

from micofx.models import SymbolConfig
from micofx.risk import MIN_PROJ_DAYS, RiskManager


def _cfg(symbol: str, *, days: float, net: float, costed: float | None = None) -> SymbolConfig:
    cfg = SymbolConfig(symbol=symbol, magic=1, enabled=True,
                       lot_mode="risk", risk_percent=2.0, sl_atr_mult=2.0)
    hold = {"net_r": net, "trades": 80}
    cfg.opt_summary = {
        "holdout": hold,
        "holdout_days": days,
        "holdout_costed": {"net_r": costed if costed is not None else net},
        "charge_costs": True,
    }
    return cfg


def _rm(cfgs: list[SymbolConfig]) -> RiskManager:
    rm = RiskManager.__new__(RiskManager)
    rm.store = _Store(cfgs)
    rm.client = _Client()
    return rm


def test_short_window_is_stretched_to_min_proj_days():
    ger = _cfg("GER40", days=36.0, net=71.7)
    rm = _rm([ger])
    rows = [{"symbol": "GER40", "enabled": True, "risk_per_trade": 10.0}]
    naive = 71.7 * 10.0 / 36.0
    guarded = 71.7 * 10.0 / MIN_PROJ_DAYS
    out = rm.fill_holdout_projection(rows, 232.0)
    assert abs(out["projected_daily"] - round(guarded, 2)) < 1e-9
    assert out["projected_daily"] < naive * 0.5
    assert "GER40" in (out.get("projected_note") or "")


def test_long_window_is_unchanged():
    xau = _cfg("XAUUSD", days=279.7, net=274.3)
    rm = _rm([xau])
    rows = [{"symbol": "XAUUSD", "enabled": True, "risk_per_trade": 10.0}]
    expected = 274.3 * 10.0 / 279.7
    out = rm.fill_holdout_projection(rows, 232.0)
    assert abs(out["projected_daily"] - round(expected, 2)) < 1e-9
    assert "XAUUSD" not in (out.get("projected_note") or "")


def test_min_lot_1r_overshoot_is_named_in_the_note():
    """US30 live 1R is ~$16 on a $222 book (min-lot concurrent), not 2%.

    That is why the chip still reads ~99%/mo after holdout_days was fixed
    to 555d. Claude's ~78% used configured 2% R. Name the gap; do not
    rewrite the dollar math (fills really take min lot).
    """
    us30 = _cfg("US30", days=555.1, net=24.97)
    rm = _rm([us30])
    rows = [{"symbol": "US30", "enabled": True, "risk_per_trade": 16.36}]
    out = rm.fill_holdout_projection(rows, 222.52)
    note = out.get("projected_note") or ""
    assert "US30" in note
    assert "min-lot" in note or "min lot" in note


def test_capacity_carries_the_short_window_note():
    ger = _cfg("GER40", days=36.0, net=71.7)
    rm = _rm([ger])
    out = rm.capacity([], {"equity": 232.0, "balance": 232.0,
                           "margin_free": 200.0, "margin": 0.0},
                      atr_by_symbol={"GER40": 40.0})
    assert "GER40" in (out.get("projected_note") or "")
    assert out["projected_monthly"] != 0.0
