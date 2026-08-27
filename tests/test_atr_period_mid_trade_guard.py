"""atr_period must not be editable while a position on that symbol is open.

Every distance engine._update_stop computes is a multiple of the live ATR - the
trail sits at ``close - trail_step_atr * atr`` and the original-risk floor is
``atr * sl_atr_mult`` - and that ATR is rebuilt from cfg.atr_period on every
cycle rather than snapshotted at entry. So changing atr_period moves an open
position's whole stop geometry exactly as trail_step_atr does.

The mid-trade guard covered trail_step_atr and its four siblings but not
atr_period, which is not an OPT_FIELD (the optimizer can never write it) and so
was easy to miss - leaving the API as an open door onto the same hazard the
guard exists for. The 409 is the same one those fields already return.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import EXIT_RISK_FIELDS, SymbolConfig
from micofx.web.app import create_app

MAGIC = 990021


def _cfg(symbol="XAUUSD", magic=MAGIC):
    return SymbolConfig(symbol=symbol, magic=magic)


class _FakeSystem:
    slippage_points = 20

    def to_dict(self):
        return {}


class _FakeStore:
    def __init__(self, symbols):
        self.symbols = symbols
        self.system = _FakeSystem()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch, source=""):
        cfg = self.symbols.get(symbol)
        if cfg is None:
            return None
        current = cfg.to_dict()
        for key, value in patch.items():
            if key in current and value is not None:
                current[key] = value
        updated = SymbolConfig.from_dict(current)
        self.symbols[symbol] = updated
        return updated


class _FakeClient:
    connected = True

    def __init__(self, open_positions=()):
        self._positions = list(open_positions)

    def positions(self, magic=None, symbol=None):
        return list(self._positions)

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return None


class _FakeEngine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


def _position():
    return {"ticket": 1, "symbol": "XAUUSD", "magic": MAGIC, "side": "buy",
            "volume": 0.1, "sl": 1990.0, "tp": 0.0, "price_open": 2000.0,
            "profit": 0.0, "swap": 0.0}


def _client(open_positions=()):
    symbols = {"XAUUSD": _cfg()}
    store = _FakeStore(symbols)
    app = create_app(store, _FakeClient(open_positions), _FakeEngine(), optimizer=None)
    return TestClient(app), store


def test_atr_period_is_covered_by_the_mid_trade_guard():
    assert "atr_period" in EXIT_RISK_FIELDS


def test_atr_period_is_not_http_writable():
    # Left the card 27.08. Mid-trade 409 stays in patch_symbol as defense
    # if the allowlist ever grows; HTTP cannot reach it today.
    tc, store = _client([_position()])
    before = store.symbols["XAUUSD"].atr_period

    res = tc.post("/api/symbols/XAUUSD", json={"atr_period": 30})

    assert res.status_code == 400
    assert "atr_period" in res.json()["detail"]
    assert store.symbols["XAUUSD"].atr_period == before


def test_atr_period_stays_closed_when_flat():
    tc, store = _client()
    before = store.symbols["XAUUSD"].atr_period
    res = tc.post("/api/symbols/XAUUSD", json={"atr_period": 30})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].atr_period == before


def test_an_unrelated_field_still_lands_while_a_position_is_open():
    # The guard must stay narrow: session hours still write; search guts
    # are a different door (hands-off 400).
    tc, store = _client([_position()])
    res = tc.post("/api/symbols/XAUUSD", json={"enabled": False})
    assert res.status_code == 200
    assert store.symbols["XAUUSD"].enabled is False


def test_writing_the_same_atr_period_back_is_still_refused():
    tc, store = _client([_position()])
    same = store.symbols["XAUUSD"].atr_period
    res = tc.post("/api/symbols/XAUUSD", json={"atr_period": same})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].atr_period == same
