"""run_id apply may override entry-gate axes (max_spread_atr) on incumbent evidence."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.web.app import create_app

HEAD = {"Origin": "http://testserver"}


class _Cfg:
    strategy = "channel_break"
    timeframe = "M30"
    magic = 990120
    max_spread_atr = 0.05


class _Store:
    def __init__(self):
        self.symbols = {"US30": _Cfg()}
        self.system = type("S", (), {"to_dict": lambda self: {}})()

    def opt_history(self, symbol, limit=40):
        return [{
            "id": 624,
            "symbol": symbol,
            "strategy": "channel_break",
            "timeframe": "M30",
            "score": 21.2,
            "validated": True,
            "holdout_days": 30.0,
            "holdout": {"net_r": 40.0, "trades": 50},
            "params": {
                "sl_atr_mult": 1.5,
                "trail_start_atr": 0.5,
                "trail_step_atr": 1.6,
                "max_spread_atr": 0.05,
            },
        }]


class _Client:
    connected = True

    def positions(self):
        return []

    def set_overrides(self, *_a, **_k):
        return None


class _Engine:
    entry_lock = __import__("threading").Lock()


class _Optimizer:
    def __init__(self, store):
        self.store = store
        self.client = _Client()
        self.entry_lock = _Engine.entry_lock
        self.last_apply: tuple | None = None

    def apply(self, symbol, params, score, detail, timeframe, strategy):
        cfg = self.store.symbols[symbol]
        self.last_apply = (symbol, dict(params), timeframe, strategy)
        cfg.max_spread_atr = params["max_spread_atr"]
        return {"ok": True, "symbol": symbol, "config": {"max_spread_atr": params["max_spread_atr"]}}


class _StoreBurstRun(_Store):
    def opt_history(self, symbol, limit=40):
        return [
            {
                "id": 632,
                "symbol": symbol,
                "strategy": "burst",
                "timeframe": "M5",
                "score": 12.0,
                "validated": True,
                "holdout_days": 30.0,
                "holdout": {"net_r": 17.0, "trades": 50},
                "params": {
                    "sl_atr_mult": 1.5,
                    "trail_start_atr": 0.5,
                    "trail_step_atr": 1.6,
                    "max_spread_atr": 0.18,
                },
            },
            super().opt_history(symbol, limit)[0],
        ]


def test_run_id_spread_override_allowed():
    store = _Store()
    opt = _Optimizer(store)
    app = create_app(store, _Client(), _Engine(), opt)
    tc = TestClient(app)
    tc.get("/")
    res = tc.post("/api/opt/apply", json={
        "symbol": "US30", "run_id": 624,
        "params": {"max_spread_atr": 0.18}, "force": True,
    }, headers=HEAD)
    assert res.status_code == 200, res.text
    assert store.symbols["US30"].max_spread_atr == 0.18


def test_run_id_exit_override_without_force_is_rejected():
    store = _Store()
    opt = _Optimizer(store)
    app = create_app(store, _Client(), _Engine(), opt)
    tc = TestClient(app)
    tc.get("/")
    res = tc.post("/api/opt/apply", json={
        "symbol": "US30", "run_id": 624,
        "params": {"trail_step_atr": 0.8}, "force": False,
    }, headers=HEAD)
    assert res.status_code == 400


def test_force_run_id_allows_measured_exit_retune():
    """US30 trail_step 2.2→0.8: costed sweep wins, WFO gate often will not."""
    store = _Store()
    opt = _Optimizer(store)
    app = create_app(store, _Client(), _Engine(), opt)
    tc = TestClient(app)
    tc.get("/")
    res = tc.post("/api/opt/apply", json={
        "symbol": "US30", "run_id": 624,
        "params": {"trail_step_atr": 0.8, "adx_min": 15.0},
        "force": True,
    }, headers=HEAD)
    assert res.status_code == 200, res.text
    assert opt.last_apply is not None
    _sym, params, _tf, _st = opt.last_apply
    assert params["trail_step_atr"] == 0.8
    assert params["adx_min"] == 15.0
    assert params["sl_atr_mult"] == 1.5  # stamped base kept


def test_gates_only_spread_zero_disables_gate():
    store = _StoreBurstRun()
    opt = _Optimizer(store)
    app = create_app(store, _Client(), _Engine(), opt)
    tc = TestClient(app)
    tc.get("/")
    store.symbols["US30"].max_spread_atr = 0.18
    res = tc.post("/api/opt/apply", json={
        "symbol": "US30", "run_id": 632,
        "params": {"max_spread_atr": 0.0},
        "force": True, "gates_only": True,
    }, headers=HEAD)
    assert res.status_code == 200, res.text
    assert store.symbols["US30"].max_spread_atr == 0.0


def test_gates_only_widens_spread_without_changing_family():
    store = _StoreBurstRun()
    opt = _Optimizer(store)
    app = create_app(store, _Client(), _Engine(), opt)
    tc = TestClient(app)
    tc.get("/")
    res = tc.post("/api/opt/apply", json={
        "symbol": "US30", "run_id": 632,
        "params": {"max_spread_atr": 0.18},
        "force": True, "gates_only": True,
    }, headers=HEAD)
    assert res.status_code == 200, res.text
    assert store.symbols["US30"].max_spread_atr == 0.18
    assert store.symbols["US30"].strategy == "channel_break"
    assert store.symbols["US30"].timeframe == "M30"
    assert opt.last_apply is not None
    _sym, params, tf, strat = opt.last_apply
    assert strat is None
    assert tf is None
    assert params == {"max_spread_atr": 0.18}
