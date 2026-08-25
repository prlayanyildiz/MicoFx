"""POST /api/holdout/capture must use the live client, not open a second bind.

gece_restart talks to this after the bot is back on 8900. A 409 while the
optimizer is busy is the other door: capture copies tens of thousands of
bars and must not contend with a search.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.bars import Bars
from micofx.engine import SPREAD_RATIO_BUCKETS
from micofx.models import SymbolConfig, SystemConfig
from micofx.web.app import create_app


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
    def __init__(self):
        cfg = SymbolConfig(symbol="GER40", magic=1, enabled=True,
                           timeframe="M30", strategy="stoch_flip")
        self.symbols = {"GER40": cfg}
        self.system = SystemConfig(
            charge_costs=True, trade_all_hours=False,
            day_end_flatten_min=0, max_cost_pct_of_risk=18.0)
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, k, default=None):
        if k == "spread_ratio":
            return {"GER40": _hist(33, 277_649)}
        return default

    def opt_params(self):
        return {"max_bars": 20000, "segments": 5}

    def opt_history(self, s, n):
        return []


class _Cli:
    connected = True
    last_error = ""
    inits = 0

    def initialize(self, *a, **k):
        self.inits += 1

    def shutdown(self):
        pass

    def set_overrides(self, m):
        pass

    def bars(self, symbol, timeframe, want):
        return _bars()

    def info(self, s):
        return {"point": 0.1, "tick_value": 1.0, "tick_size": 0.1}

    def min_stop_distance(self, s):
        return 0.5


class _Eng:
    def __init__(self):
        self.entry_lock = threading.Lock()
        self.states = {}
        self._sec_cfgs = {}


class _Opt:
    busy = False

    def status(self):
        return {"state": "idle", "busy": False}


def _tc(opt=None, client=None):
    return TestClient(create_app(_Store(), client or _Cli(), _Eng(), opt or _Opt()))


def test_capture_endpoint_uses_the_live_client(tmp_path, monkeypatch):
    monkeypatch.setattr("micofx.bar_snapshot.SNAPSHOT_DIR", tmp_path)
    client = _Cli()
    tc = _tc(client=client)
    res = tc.post("/api/holdout/capture")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["captured"] == 1
    assert client.inits == 0


def test_capture_endpoint_refuses_while_opt_is_busy():
    opt = _Opt()
    opt.busy = True
    res = _tc(opt=opt).post("/api/holdout/capture")
    assert res.status_code == 409
    assert "optimizasyon" in res.json()["detail"].lower()


def test_capture_endpoint_refuses_when_mt5_is_down():
    client = _Cli()
    client.connected = False
    res = _tc(client=client).post("/api/holdout/capture")
    assert res.status_code == 409
    assert "mt5" in res.json()["detail"].lower()
