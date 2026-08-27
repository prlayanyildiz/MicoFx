"""Leftover lot_mode=fixed must not size lots, and risk_percent is HTTP-off.

Operator 27.08: lot_for always reads stored risk_percent. The panel no
longer offers that dial; POST is 400. Switching lot_mode over HTTP is 400.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_delete_guard import _cfg, _client

from micofx.models import SymbolConfig
from micofx.store import Store


def test_patch_risk_percent_is_refused():
    cfg = _cfg("XAUUSD", magic=990021)
    cfg.lot_mode = "fixed"
    tc, store = _client({"XAUUSD": cfg}, [])
    before = store.symbols["XAUUSD"].risk_percent

    res = tc.post("/api/symbols/XAUUSD", json={"risk_percent": 1.5})
    assert res.status_code == 400, res.text
    assert store.symbols["XAUUSD"].risk_percent == before


def test_lot_mode_patch_is_refused():
    cfg = _cfg("XAUUSD", magic=990021)
    cfg.lot_mode = "fixed"
    tc, store = _client({"XAUUSD": cfg}, [])

    res = tc.post("/api/symbols/XAUUSD", json={"lot_mode": "risk", "risk_percent": 0.8})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].lot_mode == "fixed"


def test_add_symbol_is_born_on_risk_mode(tmp_path, monkeypatch):
    from micofx import store as store_module
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "lot.db")
    s = Store()
    cfg = s.add_symbol("NEWPAIR", group="forex")
    assert cfg.lot_mode == "risk"


def test_symbol_config_default_lot_mode_is_risk():
    assert SymbolConfig(symbol="X", magic=1).lot_mode == "risk"
