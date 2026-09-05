"""HTTP opt/apply refuses msa widens that fail 6-slice (SpotBrent pattern)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.web.app import create_app

HEAD = {"Origin": "http://testserver"}


class _Cfg:
    strategy = "mtf_pullback"
    timeframe = "M30"
    magic = 990099
    max_spread_atr = 0.05
    opt_score = 24.0
    use_sessions = True
    sessions = [{"start": "14:00", "end": "22:00"}]

    def to_dict(self):
        return {
            "symbol": "SpotBrent",
            "strategy": self.strategy,
            "timeframe": self.timeframe,
            "max_spread_atr": self.max_spread_atr,
            "use_sessions": self.use_sessions,
            "sessions": list(self.sessions),
        }


class _Store:
    def __init__(self):
        self.symbols = {"SpotBrent": _Cfg()}
        self.system = type("S", (), {
            "charge_costs": True,
            "to_dict": lambda self: {},
        })()

    def opt_history(self, symbol, limit=40):
        return []


class _Client:
    connected = True

    def positions(self):
        return []

    def set_overrides(self, *_a, **_k):
        return None


class _Engine:
    entry_lock = __import__("threading").Lock()

    def forget_entry_blocks(self, *_a, **_k):
        return None


class _Optimizer:
    def __init__(self, store):
        self.store = store
        self.client = _Client()
        self.entry_lock = _Engine.entry_lock
        self._force_apply = False
        self.calls = 0

    def apply(self, symbol, params, score, detail, timeframe, strategy):
        self.calls += 1
        return {"ok": True, "symbol": symbol, "config": dict(params)}

    def refresh_live_costed_stamp(self, symbol: str):
        return None


def test_opt_apply_refuses_six_slice_msa_widen():
    store = _Store()
    opt = _Optimizer(store)
    app = create_app(store, _Client(), _Engine(), opt)
    client = TestClient(app)

    with patch(
        "scripts.exec_gates.refuse_msa_widen",
        return_value="6-slice erozyon (0.05->0.08)",
    ):
        r = client.post(
            "/api/opt/apply",
            headers=HEAD,
            json={
                "symbol": "SpotBrent",
                "params": {"max_spread_atr": 0.08},
                "score": 24.0,
                "force": True,
            },
        )
    assert r.status_code == 400
    assert "6-slice" in r.json()["detail"]
    assert opt.calls == 0


def test_opt_apply_allows_when_refuse_none():
    store = _Store()
    opt = _Optimizer(store)
    app = create_app(store, _Client(), _Engine(), opt)
    client = TestClient(app)

    with patch("scripts.exec_gates.refuse_msa_widen", return_value=None):
        r = client.post(
            "/api/opt/apply",
            headers=HEAD,
            json={
                "symbol": "SpotBrent",
                "params": {"max_spread_atr": 0.08},
                "score": 24.0,
                "force": True,
            },
        )
    assert r.status_code == 200
    assert opt.calls == 1
