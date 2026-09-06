"""When live lot/1R is missing, projection must name the risk% fallback.

Claude 06.09 13:2x: Sunday restart left every symbol at lot=0 /
risk_per_trade=0. fill_holdout_projection silently switched to
balance*risk%*edge*lot_mult, and the panel read %72 instead of ~%50.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_closed_symbol_does_not_stain_projection import _Client, _Store

from micofx.models import SymbolConfig
from micofx.risk import RiskManager


def _cfg(symbol: str, *, days: float, net: float) -> SymbolConfig:
    cfg = SymbolConfig(symbol=symbol, magic=1, enabled=True,
                       lot_mode="risk", risk_percent=2.0, sl_atr_mult=2.0)
    cfg.opt_summary = {
        "holdout": {"net_r": net, "trades": 80},
        "holdout_days": days,
        "holdout_costed": {"net_r": net},
        "charge_costs": True,
    }
    return cfg


def _rm(cfgs: list[SymbolConfig]) -> RiskManager:
    rm = RiskManager.__new__(RiskManager)
    rm.store = _Store(cfgs)
    rm.client = _Client()
    rm.edge_scale = lambda cfg: 1.0  # type: ignore[method-assign]
    return rm


def test_zero_live_1r_fallback_is_named_in_projected_note():
    xau = _cfg("XAUUSD", days=280.0, net=100.0)
    ger = _cfg("GER40", days=280.0, net=50.0)
    rm = _rm([xau, ger])
    rows = [
        {"symbol": "XAUUSD", "enabled": True, "risk_per_trade": 0.0},
        {"symbol": "GER40", "enabled": True, "risk_per_trade": 0.0},
    ]
    out = rm.fill_holdout_projection(rows, 663.0)
    note = out.get("projected_note") or ""
    assert "canli lot yok" in note
    assert "risk%" in note
    assert out["projected_daily"] > 0


def test_live_1r_present_skips_fallback_note():
    xau = _cfg("XAUUSD", days=280.0, net=100.0)
    rm = _rm([xau])
    rows = [{"symbol": "XAUUSD", "enabled": True, "risk_per_trade": 11.76}]
    out = rm.fill_holdout_projection(rows, 663.0)
    note = out.get("projected_note") or ""
    assert "canli lot yok" not in note
