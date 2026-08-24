"""Midnight capture talks to an already-connected client. It must not initialize."""
from __future__ import annotations

import numpy as np
import pytest

from micofx.bars import Bars
from micofx.engine import SPREAD_RATIO_BUCKETS
from micofx.holdout_cost import capture
from micofx.models import SymbolConfig, SystemConfig


def _bars(n=900):
    rates = np.zeros(n, dtype=[
        ("time", np.int64), ("open", np.float64), ("high", np.float64),
        ("low", np.float64), ("close", np.float64), ("spread", np.float64),
        ("tick_volume", np.float64),
    ])
    rates["time"] = np.arange(n, dtype=np.int64) * 1800 + 1_700_000_000
    rates["open"] = 100.0
    rates["high"] = 101.0
    rates["low"] = 99.0
    rates["close"] = 100.5
    rates["spread"] = 2.0
    rates["tick_volume"] = 10.0
    return Bars(rates, int(rates["time"][-1] + 1800))


def _hist(bucket, count):
    counts = [0] * SPREAD_RATIO_BUCKETS
    counts[bucket] = count
    return counts


class _Store:
    def __init__(self, cfg, blob):
        self.symbols = {cfg.symbol: cfg}
        self.system = SystemConfig(
            charge_costs=True, trade_all_hours=False,
            day_end_flatten_min=0, max_cost_pct_of_risk=18.0)
        self._blob = blob

    def get_setting(self, key, default=None):
        if key == "spread_ratio":
            return self._blob
        return default

    def opt_params(self):
        return {"max_bars": 20000, "segments": 5}


class _Client:
    def __init__(self):
        self.inits = 0
        self.shutdowns = 0

    def initialize(self, *a, **k):
        self.inits += 1

    def shutdown(self):
        self.shutdowns += 1

    def bars(self, symbol, timeframe, want):
        return _bars()

    def info(self, symbol):
        return {"point": 0.1, "tick_value": 1.0, "tick_size": 0.1}

    def min_stop_distance(self, symbol):
        return 0.5


def test_capture_writes_the_pin_without_initialize(tmp_path):
    cfg = SymbolConfig(symbol="GER40", timeframe="M30", strategy="stoch_flip")
    client = _Client()
    store = _Store(cfg, {"GER40": _hist(33, 277_649)})
    path = capture(client=client, store=store, symbol="GER40", timeframe="M30",
                   path=tmp_path / "GER40_M30.npz")
    assert client.inits == 0
    assert client.shutdowns == 0
    from micofx.bar_snapshot import read
    got = read(path)
    assert got["spread_scale"] == pytest.approx(3.35, abs=0.01)
    assert got["spread_scale_n"] == 277_649
    assert got["max_cost_pct_of_risk"] == 18.0
    assert got["charge_costs"] is True


def test_capture_refuses_the_silent_one(tmp_path):
    cfg = SymbolConfig(symbol="GER40", timeframe="M30")
    client = _Client()
    store = _Store(cfg, {})
    with pytest.raises(ValueError, match="spread_scale"):
        capture(client=client, store=store, symbol="GER40", timeframe="M30",
                path=tmp_path / "x.npz")
    assert client.inits == 0


def test_capture_refuses_a_thin_histogram(tmp_path):
    """A handful of samples is the reading that already misled us once."""
    cfg = SymbolConfig(symbol="GER40", timeframe="M30")
    client = _Client()
    store = _Store(cfg, {"GER40": _hist(33, 50)})
    with pytest.raises(ValueError, match="no measured median"):
        capture(client=client, store=store, symbol="GER40", timeframe="M30",
                path=tmp_path / "thin.npz")
    assert client.inits == 0


def test_capture_accepts_a_clamped_floor_on_a_fat_histogram(tmp_path):
    """SpotBrent 24.08: median 0.95, n~310k, scale floors to 1.0.

    That 1.0 is the search's conservative floor, not a missing histogram.
    Refusing it would skip a symbol whose tick is tighter than the bar.
    """
    cfg = SymbolConfig(symbol="SpotBrent", timeframe="M30")
    client = _Client()
    # Bucket 9 centre is 0.95; _spread_scale clamps that to 1.0.
    store = _Store(cfg, {"SpotBrent": _hist(9, 309_624)})
    path = capture(client=client, store=store, symbol="SpotBrent",
                   timeframe="M30", path=tmp_path / "SpotBrent_M30.npz")
    from micofx.bar_snapshot import read
    got = read(path)
    assert got["spread_scale"] == pytest.approx(1.0)
    assert got["spread_scale_n"] == 309_624
    assert client.inits == 0


def test_capture_refuses_when_spread_scale_disagrees_with_the_histogram(tmp_path, monkeypatch):
    """_spread_scale's except path returns 1.0; this blob still has a median."""
    cfg = SymbolConfig(symbol="GER40", timeframe="M30")
    client = _Client()
    store = _Store(cfg, {"GER40": _hist(33, 277_649)})
    monkeypatch.setattr(
        "micofx.optimizer.Optimizer._spread_scale", lambda self, symbol: 1.0)
    with pytest.raises(ValueError, match="_spread_scale returned"):
        capture(client=client, store=store, symbol="GER40", timeframe="M30",
                path=tmp_path / "disagree.npz")
    assert client.inits == 0


def test_capture_refuses_a_failed_read_even_when_the_floor_is_already_one(
        tmp_path, monkeypatch):
    """SpotBrent's clamped expectation is 1.0; an except-path 1.0 matches it.

    The numeric disagreement gate cannot see that. _spread_scale_warned is
    the event: a fresh Optimizer only sets it on the except return.
    """
    cfg = SymbolConfig(symbol="SpotBrent", timeframe="M30")
    client = _Client()
    store = _Store(cfg, {"SpotBrent": _hist(9, 309_624)})

    def _fail(self, symbol):
        self._spread_scale_warned = True
        return 1.0

    monkeypatch.setattr("micofx.optimizer.Optimizer._spread_scale", _fail)
    with pytest.raises(ValueError, match="not a measurement"):
        capture(client=client, store=store, symbol="SpotBrent",
                timeframe="M30", path=tmp_path / "fail.npz")
    assert client.inits == 0
