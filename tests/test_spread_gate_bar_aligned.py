"""Unit checks for bar-aligned live spread gate helpers."""
from __future__ import annotations

from micofx.spread_gate import gate_spread_price, spread_over_cap


def test_prefer_bar_when_present():
    assert gate_spread_price(tick_spread=0.5, bar_spread=0.1) == 0.1


def test_fallback_to_tick_when_bar_missing():
    assert gate_spread_price(tick_spread=0.5, bar_spread=None) == 0.5
    assert gate_spread_price(tick_spread=0.5, bar_spread=0.0) == 0.5


def test_bar_scaled_tick_fallback_unscaled():
    """Replay multiplies bar by spread_scale; tick path stays raw."""
    assert gate_spread_price(
        tick_spread=0.5, bar_spread=0.1, spread_scale=1.25) == 0.125
    assert gate_spread_price(
        tick_spread=0.5, bar_spread=None, spread_scale=1.25) == 0.5
    assert gate_spread_price(
        tick_spread=0.5, bar_spread=0.0, spread_scale=1.25) == 0.5


def test_over_cap_identity():
    assert spread_over_cap(0.09, atr=1.0, max_spread_atr=0.08) is True
    assert spread_over_cap(0.07, atr=1.0, max_spread_atr=0.08) is False
    assert spread_over_cap(0.5, atr=1.0, max_spread_atr=0.0) is False
