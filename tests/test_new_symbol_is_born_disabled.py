"""add_symbol wrote enabled=True, so an unsearched default went live.
Found 15.08: nine operator-added symbols (FX/stock/crypto) traded on
factory t3_stoch because the enable-before-opt guard only covers PATCH,
not birth. seed_symbols already forces False; add_symbol and reset did not.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import store as store_module
from micofx.store import Store
from micofx.web.app import create_app


def test_add_symbol_is_born_disabled_even_when_asked_to_enable(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "born.db")
    s = Store()
    cfg = s.add_symbol("NEWPAIR", group="forex", enabled=True)
    assert cfg.enabled is False
    assert s.symbols["NEWPAIR"].enabled is False


def test_reset_to_preset_leaves_the_symbol_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "reset.db")
    s = Store()
    victim = next(iter(s.symbols))
    s.update_symbol(victim, {"enabled": True, "opt_updated_at": time.time()})
    updated = s.reset_symbol_to_preset(victim)
    assert updated is not None
    assert updated.enabled is False


def test_panel_add_does_not_ask_to_enable_and_warns():
    js = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static"
          / "app.js").read_text(encoding="utf-8")
    start = js.index("async function addPortfolioSymbol")
    chunk = js[start:start + 2500]
    assert "enabled: true" not in chunk
    assert "optimizasyon sonrasi acabilirsiniz" in chunk


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, m):
        pass

    def deals_since(self, since):
        return []

    def info(self, s):
        return None


class _Engine:
    def __init__(self):
        self.entry_lock = threading.Lock()
        self.states = {}
        self._sec_cfgs = {}


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25

    def _spread_scale(self, symbol):
        return 1.0


def test_create_api_returns_disabled_and_enable_without_opt_is_400(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "api.db")
    store = Store()
    tc = TestClient(create_app(store, _Client(), _Engine(), _Optimizer()))
    res = tc.post("/api/symbols", json={"symbol": "SOLUSD", "enabled": True})
    assert res.status_code == 200, res.text
    assert res.json()["config"]["enabled"] is False
    enable = tc.post("/api/symbols/SOLUSD", json={"enabled": True})
    assert enable.status_code == 400
    assert "optimize edilmeden" in enable.text
