"""A negative commission must not reach the config: it disables two risk gates.

commission_per_lot had no bounds at all. Zero is legitimate - plenty of CFD
accounts charge none - but a negative value is not, and a rebate is a
plausible reason somebody would type one.

What it breaks is entirely on the live side, which is why nothing caught it:
backtest.commission_in_price() returns 0.0 for a non-positive value, so the
walk-forward stays honest while the engine's gates come apart.

    engine._try_entry's block_high_cost gate:
        cost = commission_per_lot * lot + spread * money_per_price
    A negative commission drags cost below zero, so
    ``cost / r_value > max_cost_pct_of_risk`` can never be true and every
    entry passes regardless of spread.

    _symbol_daily_halt's floating estimate:
        profit + swap - commission_per_lot * volume
    A negative commission adds to it, so the sticky per-symbol loss halt
    trips late or never.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _System:
    slippage_points = 20

    def to_dict(self):
        return {}


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, k, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, s, n):
        return []

    def update_symbol(self, symbol, patch):
        cfg = self.symbols.get(symbol)
        cur = cfg.to_dict()
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


class _Engine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


class _Optimizer:
    def apply(self, *a, **k):
        return {"ok": True}


def _client():
    cfg = SymbolConfig(symbol="XAUUSD", magic=990021, commission_per_lot=5.0)
    store = _Store(cfg)
    return TestClient(create_app(store, _Client(), _Engine(), _Optimizer())), store


@pytest.mark.parametrize("value", [-0.01, -5.0, -100.0, -1e9])
def test_a_negative_commission_is_refused(value):
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"commission_per_lot": value})
    assert res.status_code == 400, f"{value} kabul edildi"
    assert store.symbols["XAUUSD"].commission_per_lot == 5.0


@pytest.mark.parametrize("value", [0.0, 0.5, 7.0, 250.0])
def test_a_non_negative_commission_still_goes_through(value):
    """Zero is a real setting - most CFD accounts charge no commission."""
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"commission_per_lot": value})
    assert res.status_code == 200, res.text
    assert store.symbols["XAUUSD"].commission_per_lot == value


def test_bulk_is_gated_too():
    tc, store = _client()
    res = tc.post("/api/symbols-bulk", json={"patch": {"commission_per_lot": -20.0}})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].commission_per_lot == 5.0


# ------------------------------------------------ the consequences, stated

def _cost_gate_pct(commission, lot=1.0, mppu=10.0, sl_dist=1.0, spread=0.9):
    """The arithmetic engine._try_entry runs before block_high_cost."""
    r_value = sl_dist * mppu * lot
    cost = commission * lot + spread * mppu * lot
    return cost / r_value * 100.0


def test_a_negative_commission_would_have_disabled_the_cost_gate():
    ceiling = 18.0
    # A spread eating 90% of R has to be blocked...
    assert _cost_gate_pct(0.0) > ceiling
    assert _cost_gate_pct(5.0) > ceiling
    # ...and with a negative commission it is not even close.
    assert _cost_gate_pct(-50.0) < ceiling


def _floating(commission, per_position=-30.0, volume=1.0, count=2):
    """The arithmetic _symbol_daily_halt runs on open positions."""
    return sum(per_position - commission * volume for _ in range(count))


def test_a_negative_commission_would_have_hidden_a_loss():
    assert _floating(0.0) == -60.0
    assert _floating(5.0) == -70.0          # conservative, as intended
    assert _floating(-50.0) > 0             # a 60 dollar loss reads as a profit


def test_the_walk_forward_was_never_the_problem():
    """Explains why the backtest looked healthy while the gates were off."""
    assert backtest.commission_in_price(-50.0, 1.0, 0.01) == 0.0
    assert backtest.commission_in_price(0.0, 1.0, 0.01) == 0.0
    assert backtest.commission_in_price(5.0, 1.0, 0.01) > 0.0
