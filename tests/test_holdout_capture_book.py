"""capture_book walks the live book through the already-connected client.

A second initialize() would drop the trading process. One symbol failing
must not skip the rest, or a thin histogram on SpotBrent would leave the
whole night pin empty.
"""
from __future__ import annotations

import time

import numpy as np
import pytest

from micofx import holdout_cost
from micofx.bars import Bars
from micofx.engine import SPREAD_RATIO_BUCKETS
from micofx.models import SymbolConfig, SystemConfig


def _bars(n=20000, *, stale=False):
    rates = np.zeros(n, dtype=[
        ("time", np.int64), ("open", np.float64), ("high", np.float64),
        ("low", np.float64), ("close", np.float64), ("spread", np.float64),
        ("tick_volume", np.float64),
    ])
    origin = 1_700_000_000 if stale else int(time.time()) - n * 1800
    rates["time"] = np.arange(n, dtype=np.int64) * 1800 + origin
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
    def __init__(self, symbols, blob):
        self.symbols = {c.symbol: c for c in symbols}
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
    def __init__(self, fail=(), bars=None):
        self.inits = 0
        self.shutdowns = 0
        self.connected = True
        self.fail = set(fail)
        self.asked = []
        self._bars = bars

    def initialize(self, *a, **k):
        self.inits += 1

    def shutdown(self):
        self.shutdowns += 1

    def bars(self, symbol, timeframe, want):
        self.asked.append(symbol)
        if symbol in self.fail:
            raise RuntimeError(f"{symbol}: bars refused")
        return self._bars if self._bars is not None else _bars()

    def info(self, symbol):
        return {"point": 0.1, "tick_value": 1.0, "tick_size": 0.1}

    def min_stop_distance(self, symbol):
        return 0.5


def test_capture_book_writes_enabled_symbols_without_initialize(tmp_path, monkeypatch):
    monkeypatch.setattr("micofx.bar_snapshot.SNAPSHOT_DIR", tmp_path)
    ger = SymbolConfig(symbol="GER40", timeframe="M30", strategy="stoch_flip", enabled=True)
    nas = SymbolConfig(symbol="NAS100", timeframe="M30", strategy="mtf_pullback", enabled=True)
    off = SymbolConfig(symbol="EURUSD", timeframe="M30", enabled=False)
    client = _Client()
    store = _Store([ger, nas, off], {
        "GER40": _hist(33, 277_649),
        "NAS100": _hist(33, 277_649),
        "EURUSD": _hist(33, 277_649),
    })
    out = holdout_cost.capture_book(client=client, store=store)
    assert client.inits == 0
    assert client.shutdowns == 0
    assert "EURUSD" not in client.asked
    assert set(client.asked) == {"GER40", "NAS100"}
    assert out["captured"] == 2
    assert all(r["ok"] for r in out["results"])


def test_capture_book_keeps_going_when_one_symbol_fails(tmp_path, monkeypatch):
    monkeypatch.setattr("micofx.bar_snapshot.SNAPSHOT_DIR", tmp_path)
    ger = SymbolConfig(symbol="GER40", timeframe="M30", enabled=True)
    nas = SymbolConfig(symbol="NAS100", timeframe="M30", enabled=True)
    client = _Client(fail=("GER40",))
    store = _Store([ger, nas], {
        "GER40": _hist(33, 277_649),
        "NAS100": _hist(33, 277_649),
    })
    out = holdout_cost.capture_book(client=client, store=store)
    assert client.inits == 0
    by_sym = {r["symbol"]: r for r in out["results"]}
    assert by_sym["GER40"]["ok"] is False
    assert by_sym["NAS100"]["ok"] is True
    assert out["captured"] == 1
    assert (tmp_path / "NAS100_M30.npz").exists() or any(
        p.name.startswith("NAS100") for p in tmp_path.iterdir())


def test_a_ger40_shaped_short_window_is_refused_and_keeps_the_old_file(tmp_path):
    """Live GER40 pin was 900 bars / 2023. Capture must not replace a pin."""
    dest = tmp_path / "GER40_M30.npz"
    dest.write_bytes(b"keep-me")
    cfg = SymbolConfig(symbol="GER40", timeframe="M30", enabled=True)
    client = _Client(bars=_bars(n=900))
    store = _Store([cfg], {"GER40": _hist(33, 277_649)})
    with pytest.raises(ValueError, match="too short"):
        holdout_cost.capture(client=client, store=store, symbol="GER40",
                             timeframe="M30", path=dest)
    assert dest.read_bytes() == b"keep-me"


def test_a_2023_window_is_refused_even_when_the_count_is_fat(tmp_path):
    dest = tmp_path / "GER40_M30.npz"
    dest.write_bytes(b"keep-me")
    cfg = SymbolConfig(symbol="GER40", timeframe="M30", enabled=True)
    client = _Client(bars=_bars(n=20000, stale=True))
    store = _Store([cfg], {"GER40": _hist(33, 277_649)})
    with pytest.raises(ValueError, match="stale"):
        holdout_cost.capture(client=client, store=store, symbol="GER40",
                             timeframe="M30", path=dest)
    assert dest.read_bytes() == b"keep-me"
