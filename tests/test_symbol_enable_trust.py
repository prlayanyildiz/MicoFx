"""Enabling a symbol clears AI baggage and widens spread cap."""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _System:
    slippage_points = 20

    def to_dict(self):
        return {}


class _Store:
    def __init__(self, cfg: SymbolConfig):
        self.symbols = {cfg.symbol: cfg}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, symbol, n):
        return []

    def update_symbol(self, symbol, patch, source=""):
        cur = self.symbols[symbol].to_dict()
        for k, v in patch.items():
            if k in cur and v is not None:
                cur[k] = v
        self.symbols[symbol] = SymbolConfig.from_dict(cur)
        return self.symbols[symbol]


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None

    def resolve(self, s):
        return s

    def tick(self, s):
        return None


class _Supervisor:
    def __init__(self):
        self.cleared: list[str] = []
        self.settings: dict = {}

    def update_settings(self, body):
        self.settings.update(body)
        return self.settings

    def clear(self, symbol=None):
        if symbol:
            self.cleared.append(symbol)


class _Engine:
    def __init__(self):
        self.supervisor = _Supervisor()
        self.entry_lock = threading.Lock()
        self.states = {}
        self._sec_cfgs = {}


class _Optimizer:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def _recalibrate_spread_cap(self, symbol: str, timeframe: str) -> None:
        self.calls.append((symbol, timeframe))

    def _spread_scale(self, symbol: str) -> float:
        return 1.0


def test_enabling_symbol_trusts_strategy():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1001, enabled=False, timeframe="M30")
    cfg.opt_updated_at = time.time()
    cfg.opt_score = 12.0
    cfg.strategy = "burst"
    store = _Store(cfg)
    opt = _Optimizer()
    engine = _Engine()
    tc = TestClient(create_app(store, _Client(), engine, opt))
    tc.get("/")

    res = tc.post("/api/symbols/XAUUSD", json={"enabled": True})
    assert res.status_code == 200, res.text
    assert store.symbols["XAUUSD"].enabled is True
    assert engine.supervisor.cleared == ["XAUUSD"]
    assert engine.supervisor.settings["prefer_strong_on_dd"] is False
    assert engine.supervisor.settings["hard_block_only_quarantine"] is True
    assert opt.calls == [("XAUUSD", "M30")]
