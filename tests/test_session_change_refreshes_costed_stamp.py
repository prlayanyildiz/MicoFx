"""Panel session edits must restamp charged holdout (NAS/JPN 03.09 under-weight).

Live 15-21 / 7/24 while holdout_costed still described the previous clock
made expectancy 0.046 vs 0.15 (NAS) and 0.239 vs 0.385 (JPN). Force-apply
repaired those two; the next PATCH must not leave the same hole.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer
from micofx.supervisor import Supervisor
from micofx.web.app import create_app

HEAD = {"Origin": "http://testserver"}


def _measured(**kwargs) -> dict:
    blob = {
        "trades": 373, "wins": 140, "losses": 233, "win_rate": 37.5,
        "net_r": 143.67, "expectancy": 0.385, "profit_factor": 1.56,
        "max_dd_r": 24.6, "score": 122.682, "cost_per_trade_r": 0.04,
        "cost_r": 15.0,
        "holdout_days": 555.0,
    }
    blob.update(kwargs)
    return blob


def test_refresh_live_costed_stamp_writes_measured_block():
    opt = Optimizer.__new__(Optimizer)
    opt._thread = None
    cfg = SymbolConfig(
        symbol="JPN225", magic=1, strategy="burst", timeframe="M30",
        use_sessions=False, sessions=[{"start": "23:00", "end": "08:00"}],
        opt_summary={
            "holdout": {"net_r": 99.14, "trades": 382, "expectancy": 0.26, "score": 82.66},
            "holdout_costed": {"net_r": 60.41, "trades": 253, "expectancy": 0.239, "score": 43.78},
            "charge_costs": False, "validated": True,
        },
        opt_score=82.66, opt_updated_at=100.0, validated=True,
    )
    store = MagicMock()
    store.symbols = {"JPN225": cfg}
    store.system = SystemConfig(charge_costs=True)
    store.update_symbol.side_effect = lambda symbol, patch, source="": cfg
    opt.store = store
    opt._holdout_costed = lambda *a, **k: _measured()  # type: ignore[method-assign]

    out = opt.refresh_live_costed_stamp("JPN225")
    assert out is cfg
    store.update_symbol.assert_called_once()
    patch = store.update_symbol.call_args[0][1]
    assert "opt_updated_at" not in patch
    costed = (patch["opt_summary"] or {}).get("holdout_costed")
    assert float(costed["net_r"]) == 143.67
    assert float(costed["expectancy"]) == 0.385
    assert int(costed["trades"]) >= Supervisor.MIN_COSTED_N
    assert patch["opt_summary"]["charge_costs"] is True
    assert patch["opt_score"] == 122.682
    assert float(patch["opt_summary"]["holdout_days"]) == 555.0


def test_refresh_skips_when_optimizer_busy():
    opt = Optimizer.__new__(Optimizer)
    opt._thread = type("T", (), {"is_alive": lambda self: True})()
    cfg = SymbolConfig(symbol="NAS100", magic=1)
    store = MagicMock()
    store.symbols = {"NAS100": cfg}
    opt.store = store
    opt._holdout_costed = lambda *a, **k: _measured()  # type: ignore[method-assign]
    assert opt.refresh_live_costed_stamp("NAS100") is None
    store.update_symbol.assert_not_called()


def test_refresh_skips_thin_costed():
    opt = Optimizer.__new__(Optimizer)
    opt._thread = None
    cfg = SymbolConfig(symbol="US30", magic=1, opt_summary={"holdout_costed": {"trades": 253}})
    store = MagicMock()
    store.symbols = {"US30": cfg}
    store.system = SystemConfig(charge_costs=True)
    opt.store = store
    opt._holdout_costed = lambda *a, **k: _measured(trades=17, net_r=3.0)  # type: ignore[method-assign]
    assert opt.refresh_live_costed_stamp("US30") is None
    store.update_symbol.assert_not_called()


class _Store:
    def __init__(self):
        self.system = SystemConfig(charge_costs=True)
        self.defaults = {"symbols": [], "group_presets": {}}
        self.symbols = {
            "NAS100": SymbolConfig(
                symbol="NAS100", magic=1, enabled=True,
                strategy="mtf_pullback", timeframe="M30",
                use_sessions=True,
                sessions=[{"start": "14:00", "end": "22:00"}],
                opt_summary={
                    "holdout_costed": {
                        "net_r": 72.36, "trades": 1559, "expectancy": 0.046,
                        "score": 32.13, "profit_factor": 1.07,
                    },
                    "charge_costs": False, "validated": True,
                },
                opt_updated_at=1.0, opt_score=32.13, validated=True,
            ),
        }

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch, source=""):
        cfg = self.symbols[symbol]
        for key, value in patch.items():
            setattr(cfg, key, value)
        return cfg


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return {"name": symbol, "volume_min": 0.01, "volume_step": 0.01,
                "digits": 2, "description": symbol}


class _Engine:
    entry_lock = __import__("threading").Lock()

    def refresh_account(self, force=False):
        return {}


def test_panel_session_patch_refreshes_costed_stamp():
    store = _Store()
    opt = Optimizer.__new__(Optimizer)
    opt._thread = None
    opt.store = store
    opt.refresh_live_costed_stamp = MagicMock(return_value=store.symbols["NAS100"])
    app = create_app(store, _Client(), _Engine(), optimizer=opt)
    tc = TestClient(app)
    res = tc.post(
        "/api/symbols/NAS100",
        json={"sessions": [{"start": "15:00", "end": "21:00"}]},
        headers=HEAD,
    )
    assert res.status_code == 200, res.text
    opt.refresh_live_costed_stamp.assert_called_once_with("NAS100")


def test_unrelated_patch_does_not_refresh_stamp():
    store = _Store()
    opt = Optimizer.__new__(Optimizer)
    opt._thread = None
    opt.refresh_live_costed_stamp = MagicMock()
    app = create_app(store, _Client(), _Engine(), optimizer=opt)
    tc = TestClient(app)
    res = tc.post(
        "/api/symbols/NAS100",
        json={"group": "index"},
        headers=HEAD,
    )
    assert res.status_code == 200, res.text
    opt.refresh_live_costed_stamp.assert_not_called()
