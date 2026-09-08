"""Capacity SL distance must use the same shakeout mult as live entry."""
from __future__ import annotations

from types import SimpleNamespace

from micofx.models import SymbolConfig
from micofx.risk import size_sl_distance


def test_size_sl_distance_honours_shakeout_mult():
    cfg = SymbolConfig(symbol="XAUUSD", sl_atr_mult=1.0)
    client = SimpleNamespace(min_stop_distance=lambda s: 0.1)
    raw = size_sl_distance(cfg, atr=10.0, client=client)
    floored = size_sl_distance(cfg, atr=10.0, client=client, sl_atr_mult=1.5)
    assert raw == 10.0
    assert floored == 15.0
