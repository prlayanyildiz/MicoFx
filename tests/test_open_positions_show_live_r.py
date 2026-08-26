"""Open rows must carry live R from the fill-time stop, not cash alone.

The panel showed TP (always 0) and dollar P/L. Autopsy already knew NAS100
winners kept 0.32 of MFE — but an open ticket that had run 2.7R and sat at
0.3R looked like a quiet +7 dollars. Harvest math belongs on the live row.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


def _eng(**book) -> Engine:
    eng = Engine.__new__(Engine)
    cfg = SimpleNamespace(magic=14, symbol="NAS100", group="index",
                          partial_at_r=0.0, breakeven_at_r=1.5)
    eng.store = SimpleNamespace(symbols={"NAS100": cfg})
    eng.execution = SimpleNamespace(snapshot=lambda _t: dict(book))
    eng._scale_out_done = set()
    return eng


def test_buy_r_open_uses_original_sl_not_the_trail():
    eng = _eng(original_sl=100.0, risk_dist=2.0, mfe=3.0, mae=0.4)
    pos = {
        "ticket": 1, "symbol": "NAS100", "magic": 14, "side": "buy",
        "volume": 0.3, "price_open": 102.0, "price_current": 103.5,
        "sl": 102.2, "tp": 0.0, "profit": 4.5, "swap": 0.0, "time": 1,
        "comment": "MicoFX",
    }
    row = eng._decorate_positions([pos])[0]
    # Original risk is |102-100|=2, not the trailed |103.5-102.2|.
    assert row["r_open"] == 0.75
    assert row["mfe_r"] == 1.5
    assert row["trail_moved"] is True
    assert row["be_locked"] is True
    assert row["partial_done"] is False
    assert row["tp"] == 0.0


def test_short_r_open_is_coverable_price_over_original_risk():
    eng = _eng(original_sl=53642.7, risk_dist=17.8, mfe=14.8, mae=2.0)
    pos = {
        "ticket": 2, "symbol": "NAS100", "magic": 14, "side": "sell",
        "volume": 1.0, "price_open": 53624.9, "price_current": 53610.1,
        "sl": 53642.7, "tp": 0.0, "profit": 14.8, "swap": 0.0, "time": 1,
        "comment": "MicoFX",
    }
    row = eng._decorate_positions([pos])[0]
    assert row["r_open"] == 0.8315
    assert row["trail_moved"] is False
    assert row["be_locked"] is False


def test_partial_done_follows_scale_out_set():
    eng = _eng(original_sl=100.0, risk_dist=1.0, mfe=0.0, mae=0.0)
    eng._scale_out_done = {9}
    pos = {
        "ticket": 9, "symbol": "NAS100", "magic": 14, "side": "buy",
        "volume": 0.2, "price_open": 100.5, "price_current": 100.4,
        "sl": 100.0, "tp": 0.0, "profit": -1.0, "swap": 0.0, "time": 1,
        "comment": "MicoFX",
    }
    assert eng._decorate_positions([pos])[0]["partial_done"] is True


def test_harvest_view_counts_winner_leftover_only():
    eng = Engine.__new__(Engine)
    eng.store = SimpleNamespace(symbols={
        "NAS100": SimpleNamespace(partial_at_r=0.0, symbol="NAS100"),
        "GER40": SimpleNamespace(partial_at_r=1.5, symbol="GER40"),
    })
    eng._trade_autopsies = [
        {"symbol": "NAS100", "r_realised": 0.31, "left_on_table_r": 2.44,
         "exit_reason": "trail", "held_min": 40},
        {"symbol": "NAS100", "r_realised": -1.0, "left_on_table_r": 1.77,
         "exit_reason": "sl", "held_min": 12},
        {"symbol": "GER40", "r_realised": 4.08, "left_on_table_r": 3.38,
         "exit_reason": "trail", "held_min": 90},
    ]
    view = eng._harvest_view()
    assert view["n"] == 3
    assert view["left_on_table_r"] == 5.82
    assert view["by_symbol"]["NAS100"] == 2.44
    assert view["by_symbol"]["GER40"] == 3.38
    assert view["partial_on"] == ["GER40"]
