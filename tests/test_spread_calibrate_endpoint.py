"""POST /api/symbols/{symbol}/spread-calibrate re-reads max_spread_atr safely."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.web.app import create_app

HEAD = {"Origin": "http://testserver"}


class _Cfg:
    def __init__(self, cap: float = 0.05, tf: str = "M30"):
        self.max_spread_atr = cap
        self.timeframe = tf
        self.opt_summary = {}


class _Store:
    def __init__(self):
        self.symbols = {"US30": _Cfg(0.05)}
        self.system = type("S", (), {"to_dict": lambda self: {}})()


class _Client:
    connected = True

    def set_overrides(self, *_a, **_k):
        return None


class _Engine:
    running = True


class _Optimizer:
    def __init__(self, store: _Store):
        self.store = store
        self.calls: list[tuple[str, str]] = []

    def _recalibrate_spread_cap(self, symbol: str, timeframe: str) -> None:
        self.calls.append((symbol, timeframe))
        cfg = self.store.symbols["US30"]
        cfg.max_spread_atr = 0.12
        cfg.opt_summary = {"spread_recalibrated_from": 0.05, "spread_recalibrated_to": 0.12}


def _tc() -> TestClient:
    store = _Store()
    opt = _Optimizer(store)
    app = create_app(store, _Client(), _Engine(), opt)
    tc = TestClient(app)
    tc.get("/")
    return tc, store, opt


def test_spread_calibrate_calls_optimizer_and_returns_caps():
    tc, store, opt = _tc()
    res = tc.post("/api/symbols/US30/spread-calibrate", headers=HEAD)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["symbol"] == "US30"
    assert body["before"] == 0.05
    assert body["after"] == 0.12
    assert body["changed"] is True
    assert opt.calls == [("US30", "M30")]


def test_spread_calibrate_unknown_symbol_404():
    tc, _, _ = _tc()
    res = tc.post("/api/symbols/NOPE/spread-calibrate", headers=HEAD)
    assert res.status_code == 404
