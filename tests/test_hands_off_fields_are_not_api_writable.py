"""Hands-off means the API door, not only the panel.

The terminal hid plumbing, cost toggles, supervisor knobs and strategy guts
so they would not be flipped by accident. POST /api/system and friends still
accepted the same keys, so an Origin-bearing agent could turn harvest-adjacent
cost flags or lot_multiplier without a control on screen. Apply() and Store
still write search-owned fields; this only closes the HTTP hole.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig, SystemConfig
from micofx.web.app import create_app


class _Store:
    def __init__(self):
        self.system = SystemConfig(lot_multiplier=1.0, charge_costs=True)
        self.symbols = {
            "XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1, t3_length=6,
                                   max_positions=1, enabled=False,
                                   sl_atr_mult=1.5, harvest_at_r=0.0),
        }
        self.defaults = {"symbols": [], "group_presets": {}}
        self.saved_opt = None
        self.reset_opt = False
        self.reset_symbol = False

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass

    def opt_params(self):
        return {}

    def save_opt_params(self, params):
        self.saved_opt = params
        return params

    def reset_opt_params(self):
        self.reset_opt = True
        return {}

    def reset_symbol_to_preset(self, symbol, avoid_magics=None):
        self.reset_symbol = True
        return self.symbols[symbol]

    def update_system(self, patch, source=""):
        current = self.system.to_dict()
        for key, value in patch.items():
            if value is not None:
                current[key] = value
        self.system = SystemConfig.from_dict(current)
        return self.system

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
        return None


class _Supervisor:
    def __init__(self):
        self.settings = {"enabled": True, "quarantine_hours": 12}
        self.update_calls = []

    def update_settings(self, patch):
        self.update_calls.append(patch)
        self.settings.update(patch)
        return self.settings

    def status(self):
        return {"settings": self.settings}


class _Engine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}
        self.supervisor = _Supervisor()


def _client():
    store = _Store()
    engine = _Engine()
    app = create_app(store, _Client(), engine, optimizer=None)
    return TestClient(app), store, engine


def test_lot_multiplier_is_writable_for_deleverage():
    tc, store, _ = _client()
    before = store.system.lot_multiplier
    res = tc.post("/api/system", json={"lot_multiplier": 1.0})
    assert res.status_code == 200, res.text
    assert store.system.lot_multiplier == 1.0
    store.update_system({"lot_multiplier": before}, source="test restore")


def test_system_cost_toggles_are_writable_for_zero_cost_book():
    tc, store, _ = _client()
    res = tc.post("/api/system", json={
        "charge_costs": False,
        "block_high_cost": False,
        "max_cost_pct_of_risk": 0.0,
    })
    assert res.status_code == 200, res.text
    assert store.system.charge_costs is False
    assert store.system.block_high_cost is False
    assert store.system.max_cost_pct_of_risk == 0.0


def test_system_plumbing_still_blocks_unknown_keys():
    tc, store, _ = _client()
    before = store.system.max_lot
    res = tc.post("/api/system", json={"max_lot": 0.5})
    assert res.status_code == 400
    assert store.system.max_lot == before


def test_operator_system_dials_still_write():
    tc, store, _ = _client()
    res = tc.post("/api/system", json={"max_margin_usage_pct": 55.0})
    assert res.status_code == 200, res.text
    assert store.system.max_margin_usage_pct == 55.0


def test_system_lot_and_position_caps_are_not_writable():
    tc, store, _ = _client()
    before_pos = store.system.max_positions
    before_lot = store.system.max_lot
    res = tc.post("/api/system", json={"max_positions": 2, "max_lot": 0.5})
    assert res.status_code == 400, res.text
    assert store.system.max_positions == before_pos
    assert store.system.max_lot == before_lot


def test_autostart_mt5_is_writable():
    """Operator: terminal kapaliysa bot acsin, panelden kapatilabilsin."""
    tc, store, _ = _client()
    res = tc.post("/api/system", json={"autostart_mt5": True})
    assert res.status_code == 200, res.text
    assert store.system.autostart_mt5 is True


def test_autostart_bot_is_writable():
    """Reboot must not wait for a click. running is still not auto-resumed."""
    tc, store, _ = _client()
    res = tc.post("/api/system", json={"autostart_bot": True})
    assert res.status_code == 200, res.text
    assert store.system.autostart_bot is True


def test_total_slot_cap_is_not_writable():
    tc, store, _ = _client()
    before = store.system.max_total_positions
    res = tc.post("/api/system", json={"max_total_positions": 40})
    assert res.status_code == 400, res.text
    assert store.system.max_total_positions == before


def test_concurrent_risk_is_writable():
    tc, store, _ = _client()
    before = store.system.max_concurrent_risk_pct
    res = tc.post("/api/system", json={"max_concurrent_risk_pct": 30.0})
    assert res.status_code == 200, res.text
    assert store.system.max_concurrent_risk_pct == 30.0
    store.update_system({"max_concurrent_risk_pct": before}, source="test restore")


def test_daily_loss_pct_is_writable_to_arm_the_brake():
    """Operator 03.09: daily brake may be armed at the shipped 3% default."""
    tc, store, _ = _client()
    res = tc.post("/api/system", json={"daily_loss_pct": 3.0})
    assert res.status_code == 200, res.text
    assert store.system.daily_loss_pct == 3.0


def test_daily_flatten_and_edge_sizing_are_not_writable():
    tc, store, _ = _client()
    before_flat = store.system.daily_loss_flatten
    before_edge = store.system.size_by_edge
    for key, value in (
        ("daily_loss_flatten", False),
        ("size_by_edge", False),
    ):
        res = tc.post("/api/system", json={key: value})
        assert res.status_code == 400, (key, res.text)
    assert store.system.daily_loss_flatten == before_flat
    assert store.system.size_by_edge == before_edge


def test_unc_latch_is_not_http_writable():
    tc, store, _ = _client()
    res = tc.post("/api/system", json={"backup_dir_allow_unc": True})
    assert res.status_code == 400
    assert store.system.backup_dir_allow_unc is False


def test_supervisor_knobs_are_not_writable():
    tc, store, engine = _client()
    res = tc.post("/api/ai/settings", json={"quarantine_hours": 24})
    assert res.status_code == 400
    assert engine.supervisor.update_calls == []
    assert engine.supervisor.settings["quarantine_hours"] == 12


def test_ai_enabled_still_writes():
    tc, store, engine = _client()
    res = tc.post("/api/ai/settings", json={"enabled": False})
    assert res.status_code == 200, res.text
    assert engine.supervisor.update_calls == [{"enabled": False}]


def test_strategy_guts_are_not_writable():
    tc, store, _ = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"t3_length": 9})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].t3_length == 6


def test_position_sizing_is_not_writable():
    tc, store, _ = _client()
    before = store.symbols["XAUUSD"].risk_percent
    res = tc.post("/api/symbols/XAUUSD", json={"risk_percent": 0.8})
    assert res.status_code == 400, res.text
    assert store.symbols["XAUUSD"].risk_percent == before


def test_symbol_lot_and_margin_caps_are_not_writable():
    """Operator 28.08: leftover knobs unread. System sizes from margin + denetci."""
    tc, store, _ = _client()
    before = store.symbols["XAUUSD"]
    res = tc.post("/api/symbols/XAUUSD", json={
        "max_lot": 0.5, "max_margin_pct": 15.0, "max_positions": 1,
    })
    assert res.status_code == 400, res.text
    assert store.symbols["XAUUSD"].max_lot == before.max_lot
    assert store.symbols["XAUUSD"].max_margin_pct == before.max_margin_pct
    assert store.symbols["XAUUSD"].max_positions == before.max_positions


def test_enabled_still_writes():
    tc, store, _ = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"enabled": False})
    assert res.status_code == 200, res.text
    assert store.symbols["XAUUSD"].enabled is False


def test_family_and_tf_are_not_writable():
    tc, store, _ = _client()
    before = store.symbols["XAUUSD"].strategy
    res = tc.post("/api/symbols/XAUUSD", json={"strategy": "burst", "timeframe": "M30"})
    assert res.status_code == 400
    assert "strategy" in res.json()["detail"]
    assert store.symbols["XAUUSD"].strategy == before


def test_magic_is_not_writable():
    tc, store, _ = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"magic": 990099})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].magic == 1


def test_exit_readout_is_not_writable():
    tc, store, _ = _client()
    before = store.symbols["XAUUSD"].sl_atr_mult
    res = tc.post("/api/symbols/XAUUSD", json={"sl_atr_mult": 2.0})
    assert res.status_code == 400
    assert "sl_atr_mult" in res.json()["detail"]
    assert store.symbols["XAUUSD"].sl_atr_mult == before


def test_harvest_overlay_is_not_writable():
    tc, store, _ = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"harvest_at_r": 1.5})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].harvest_at_r == 0.0


def test_opt_grid_is_not_writable():
    """Narrowed 01.09: cost axes are writable (F49), every other axis is not.

    See tests/test_the_cost_axis_can_reach_its_own_floor.py for why the door
    opened at all - the search could not tighten a gate its own grid floor had
    put out of reach.
    """
    tc, store, _ = _client()
    res = tc.post("/api/opt/params", json={"grid": {"sl_atr_mult": [1.0, 2.0]}})
    assert res.status_code == 400
    assert "sl_atr_mult" in res.json()["detail"]
    assert store.saved_opt is None


def test_opt_depth_dials_still_write():
    tc, store, _ = _client()
    res = tc.post("/api/opt/params", json={
        "lookback_days": 180, "refine_rounds": 1, "max_combos": 2000,
    })
    assert res.status_code == 200, res.text
    assert store.saved_opt["lookback_days"] == 180
    assert store.saved_opt["max_combos"] == 2000


def test_symbol_reset_is_not_writable():
    tc, store, _ = _client()
    res = tc.post("/api/symbols/XAUUSD/reset")
    assert res.status_code == 400
    assert store.reset_symbol is False


def test_opt_params_reset_is_not_writable():
    tc, store, _ = _client()
    res = tc.post("/api/opt/params/reset")
    assert res.status_code == 400
    assert store.reset_opt is False
