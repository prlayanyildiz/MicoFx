from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
from fastapi.testclient import TestClient

from micofx.engine import Engine
from micofx.store import Store
from micofx.strategy import IndicatorCache, Params, compute
from micofx.web.app import create_app


def test_burst_near_miss_reported_in_signals():
    n = 300
    times = np.arange(n, dtype=np.int64) * 1800
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    high = np.full(n, 101.0)
    low = np.full(n, 99.0)
    # Expansion candle with close near high, but volume ratio low
    high[-1] = 105.0
    low[-1] = 99.0
    close[-1] = 104.5
    open_[-1] = 100.0
    volume = np.ones(n)
    volume[-1] = 1.0  # volume ratio ~ 1.0, but vol_ratio_min requires 1.35

    cache = IndicatorCache(high, low, close, times, tf_seconds=1800, open_=open_, volume=volume)
    p = Params(strategy="burst", brst_lookback=20, brst_range_z=1.0, brst_close_pct=0.6,
               vol_ratio_min=1.35)
    sig = compute(cache, p)
    snap = sig.last()

    assert not snap.get("buy")
    assert not snap.get("sell")
    nm = snap.get("near_miss")
    assert nm is not None
    assert nm["strategy"] == "burst"
    assert nm["side"] == "buy"
    assert any("vol_ratio" in r for r in nm["reasons"])


def test_channel_break_near_miss_reported():
    n = 300
    times = np.arange(n, dtype=np.int64) * 1800
    close = np.linspace(100.0, 110.0, n)
    open_ = close - 0.2
    high = close + 0.5
    low = close - 0.5
    close[-1] = 110.6
    high[-1] = 111.0
    volume = np.ones(n)

    cache = IndicatorCache(high, low, close, times, tf_seconds=1800, open_=open_, volume=volume)
    p = Params(strategy="channel_break", chan_lookback=20, vol_ratio_min=1.35)
    sig = compute(cache, p)
    snap = sig.last()

    nm = snap.get("near_miss")
    if not snap.get("buy"):
        assert nm is not None
        assert nm["strategy"] == "channel_break"


def test_engine_missed_trades_ring():
    store = MagicMock(spec=Store)
    store.get_setting.return_value = []
    store.symbols = {}
    store.system = MagicMock()
    client = MagicMock()
    client.broker_now.return_value = 1700000000.0

    engine = Engine(store, client)
    assert len(engine._missed_trades) == 0

    engine._record_missed_trade("BTCUSD", "near_miss", "range_z", "buy", 60000.0, 123)
    engine._record_missed_trade("GER40", "gate_blocked", "seans_kapali", "buy", 18000.0, 124)

    data = engine.missed_trades()
    assert data["total"] == 2
    assert data["by_symbol"]["BTCUSD"] == 1
    assert data["by_symbol"]["GER40"] == 1
    assert data["by_category"]["near_miss"] == 1
    assert data["by_category"]["gate_blocked"] == 1

    engine._record_missed_trade("GER40", "gate_blocked", "seans_kapali", "buy", 18000.0, 124)
    assert engine.missed_trades()["total"] == 2

    engine.reset_missed_trades()
    assert engine.missed_trades()["total"] == 0


def test_web_missed_trades_endpoint():
    store = MagicMock(spec=Store)
    store.get_setting.return_value = []
    store.symbols = {}
    store.system = MagicMock()
    client = MagicMock()
    client.broker_now.return_value = 1700000000.0
    engine = Engine(store, client)
    app = create_app(store, client, engine, optimizer=MagicMock())

    tc = TestClient(app)
    resp = tc.get("/api/analysis/missed-trades")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "total" in data
    assert "by_symbol" in data
    assert "events" in data
    assert "note" in data
