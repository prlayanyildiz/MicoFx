"""Stop-leg adverse must be fill vs SL, not a tautology.

Paper (a5562e9) exits at the stop price when the bar trades through it.
Live scoring compares the broker deal price to the SL last seen on the
ticket. If those two arguments are the same object, or the deal price is
replaced with the SL before the compare, every stop sample is zero by
definition and the 217 live zeros are not evidence of a perfect venue.

Fail-first: a long stopped 0.5 below its SL must report adverse 0.5.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.execution import DEAL_REASON_SL, ExecutionMonitor


class _Store:
    def __init__(self):
        self.data = {}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


class _Client:
    def info(self, symbol):
        return {"point": 0.01}

    def money_per_price_unit(self, symbol, volume):
        return 1.0


def _reap(sl: float, fill: float, side: str = "buy") -> dict:
    mon = ExecutionMonitor(_Store())
    mon.track([{
        "ticket": 1, "symbol": "GER40", "side": side, "sl": sl, "tp": 0.0,
        "price_open": sl + (1.0 if side == "buy" else -1.0), "magic": 1,
    }])
    gone = mon.track([])
    mon.reap(gone, [{
        "position": 1, "ticket": 10, "reason": DEAL_REASON_SL, "symbol": "GER40",
        "magic": 1, "volume": 0.1, "price": fill, "profit": -1.0,
        "commission": 0.0, "swap": 0.0,
    }], _Client())
    rows = mon._samples.get("GER40") or []
    assert rows, "stop bacağı örnek üretmedi"
    return rows[-1]


def test_a_stop_fill_worse_than_the_sl_is_adverse():
    """Long: SL 100, fill 99.5. Closing sell is worse (lower). adverse = 0.5."""
    row = _reap(sl=100.0, fill=99.5, side="buy")
    assert row["leg"] == "stop"
    assert row["adverse"] == 0.5, (
        f"SL=100 fill=99.5 iken adverse {row['adverse']!r} - "
        f"kayıt SL'ye karşı değil ya da ikisi aynı sayı"
    )


def test_a_short_stop_fill_worse_than_the_sl_is_adverse():
    """Short: SL 100, fill 100.5. Closing buy is worse (higher)."""
    row = _reap(sl=100.0, fill=100.5, side="sell")
    assert row["adverse"] == 0.5, f"short stop adverse {row['adverse']!r}"


def test_an_exact_sl_fill_is_zero_adverse():
    """The live 217 zeros are only honest if this path can also be non-zero."""
    row = _reap(sl=100.0, fill=100.0, side="buy")
    assert row["adverse"] == 0.0


def test_chunked_stop_slippage_uses_the_volume_weighted_fill():
    """A stop that fills in two prints, the last of them sitting on the SL,
    must not report zero adverse. reap() already volume-weights the price for
    the log line; scoring used to take chunks[-1]['price'] instead, which is
    the SL whenever the broker's last print is the stop level.
    """
    mon = ExecutionMonitor(_Store())
    mon.track([{
        "ticket": 1, "symbol": "GER40", "side": "buy", "sl": 100.0, "tp": 0.0,
        "price_open": 101.0, "magic": 1,
    }])
    gone = mon.track([])
    mon.reap(gone, [
        {"position": 1, "ticket": 10, "reason": DEAL_REASON_SL, "symbol": "GER40",
         "magic": 1, "volume": 0.2, "price": 99.0, "profit": -0.8,
         "commission": 0.0, "swap": 0.0},
        {"position": 1, "ticket": 11, "reason": DEAL_REASON_SL, "symbol": "GER40",
         "magic": 1, "volume": 0.1, "price": 100.0, "profit": -0.2,
         "commission": 0.0, "swap": 0.0},
    ], _Client())
    row = (mon._samples.get("GER40") or [None])[-1]
    assert row, "örnek yok"
    # VWAP = (99*0.2 + 100*0.1)/0.3 = 99.333...; long close worse by 0.666...
    assert abs(row["adverse"] - (100.0 - 99.33333333333333)) < 1e-6, (
        f"parçalı stop adverse {row['adverse']!r}, son print SL'de sıfırlanır"
    )
