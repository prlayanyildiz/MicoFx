"""Fill-time original_sl must survive zero/negative MT5 report prices."""
from __future__ import annotations

from micofx.engine import _fill_log_price, _fill_original_sl


def test_reported_sl_wins_when_positive():
    assert _fill_original_sl("buy", 100.0, 5.0, 95.0) == 95.0


def test_computed_sl_when_report_is_zero():
    assert _fill_original_sl("buy", 25874.0, 49.5, 0.0) == 25824.5
    assert _fill_original_sl("sell", 29000.0, 120.0, -119.8) == 29120.0


def test_fill_log_price_uses_fallback():
    assert _fill_log_price({"price": 0.0}, 25874.0) == 25874.0
    assert _fill_log_price({"price": 25880.0}, 25874.0) == 25880.0
