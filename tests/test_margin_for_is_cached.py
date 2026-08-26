"""order_calc_margin is an MT5 lock hold; capacity() called it per symbol
on every panel poll. A few seconds of reuse is the dashboard, not sizing.
"""
from __future__ import annotations

import time

from micofx import mt5client as m


class _Cli(m.MT5Client):
    def __init__(self):
        super().__init__()
        self.connected = True
        self.calc_calls = 0

    def select(self, symbol):
        return symbol

    def tick(self, symbol):
        return {"bid": 1.0, "ask": 1.1, "time": time.time(), "spread": 0.1}


def test_margin_for_reuses_a_fresh_result(monkeypatch):
    cli = _Cli()

    def _calc(order_type, real, volume, price):
        cli.calc_calls += 1
        return 12.5

    monkeypatch.setattr(m, "mt5", type("M", (), {
        "ORDER_TYPE_BUY": 0, "ORDER_TYPE_SELL": 1,
        "order_calc_margin": staticmethod(_calc),
    })())
    a = cli.margin_for("GER40", 0.8, "buy")
    b = cli.margin_for("GER40", 0.8, "buy")
    assert a == b == 12.5
    assert cli.calc_calls == 1
