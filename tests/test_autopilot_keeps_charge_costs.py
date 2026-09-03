"""Autopilot must not flip charge_costs off just because commission is 0.

CFD books often have commission_per_lot=0 while spread is the real cost.
Turning charge_costs off made WFO pick paper-optimal SL (Claude 03.09
autopsy: GER40/BTC mis-tuned; live GER40/US30 force-WFO ran cost_r=0).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import AutoPilot
from micofx.models import SymbolConfig, SystemConfig


class _Store:
    def __init__(self):
        self.system = SystemConfig(
            autopilot_enabled=True,
            charge_costs=True,
            block_high_cost=True,
            max_cost_pct_of_risk=25.0,
            autostart_bot=True,
            kasa_auto_enabled=False,
        )
        self.symbols = {
            "GER40": SymbolConfig(
                symbol="GER40", magic=1, enabled=True, commission_per_lot=0.0),
            "US30": SymbolConfig(
                symbol="US30", magic=2, enabled=True, commission_per_lot=0.0),
        }
        self.patches: list[dict] = []

    def update_system(self, patch, source=""):
        self.patches.append({"patch": dict(patch), "source": source})
        for k, v in patch.items():
            setattr(self.system, k, v)
        return self.system

    def get_setting(self, key, default=None):
        return default


class _Engine:
    def __init__(self, store):
        self.store = store
        self.client = None
        self.supervisor = None
        self._positions = []

    def entry_blocks(self):
        return {"since": 0.0, "rows": []}


def test_autopilot_does_not_disable_charge_costs_when_commission_is_zero():
    store = _Store()
    ap = AutoPilot(_Engine(store))
    notes = ap._apply_cost_free()
    assert store.system.charge_costs is True
    assert store.system.block_high_cost is True
    assert not any(p["patch"].get("charge_costs") is False for p in store.patches)
    assert notes == [] or all("charge_costs=false" not in n for n in notes)
