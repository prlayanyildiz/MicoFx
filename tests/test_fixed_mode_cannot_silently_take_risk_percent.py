"""``risk_percent`` on a fixed-lot symbol was a silent no-op.

Found live: every book symbol was ``lot_mode=fixed``. The operator raised
``risk_percent`` 0.5 → 1.5; the API answered ``ok:true`` and the panel still
showed the field. ``lot_for`` returns on the first line and never reads
risk_percent, so nothing sized changed. That is the same silent-accept class
the rest of the panel already refuses.

A PATCH that writes ``risk_percent`` while the resulting mode is still
``fixed`` must not look successful. Switching to risk in the same body is
allowed - that is how the field becomes live.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_delete_guard import _cfg, _client

from micofx.models import SymbolConfig
from micofx.store import Store


def test_patch_risk_percent_on_fixed_mode_is_refused():
    cfg = _cfg("XAUUSD", magic=990021)
    cfg.lot_mode = "fixed"
    tc, store = _client({"XAUUSD": cfg}, [])

    res = tc.post("/api/symbols/XAUUSD", json={"risk_percent": 1.5})
    assert res.status_code == 400
    assert "fixed modda kullanilmiyor" in res.json()["detail"]
    assert store.symbols["XAUUSD"].risk_percent != 1.5


def test_same_patch_may_switch_to_risk_and_set_percent():
    cfg = _cfg("XAUUSD", magic=990021)
    cfg.lot_mode = "fixed"
    tc, store = _client({"XAUUSD": cfg}, [])

    res = tc.post("/api/symbols/XAUUSD", json={"lot_mode": "risk", "risk_percent": 0.8})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].lot_mode == "risk"
    assert store.symbols["XAUUSD"].risk_percent == pytest.approx(0.8)


def test_add_symbol_is_born_on_risk_mode(tmp_path, monkeypatch):
    """Factory default was ``fixed``; a new name inherited the dead path."""
    from micofx import store as store_module
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "lot.db")
    s = Store()
    cfg = s.add_symbol("NEWPAIR", group="forex")
    assert cfg.lot_mode == "risk"


def test_symbol_config_default_lot_mode_is_risk():
    assert SymbolConfig(symbol="X", magic=1).lot_mode == "risk"
