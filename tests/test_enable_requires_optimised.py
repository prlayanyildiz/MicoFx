"""A symbol may not be switched on until the optimizer has chosen its config.

EURUSD reached ``enabled`` carrying nothing but the dataclass defaults -
opt_updated_at 0.0, opt_score 0.0, an empty opt_summary and t3_stoch/M5. That
is not a config the search picked, it is the factory setting, and the search
had already refused this symbol outright: 365 days, four timeframes, fourteen
families, no candidate cleared the accept gate. On M5 an FX symbol pays 25-28%
of risk in spread against an 18% live ceiling, so it would either be refused
at the gate on every signal or fill on parameters nothing has validated.

The same state is one restore away for the whole book. config/defaults.json
seeds symbol, group, magic, sessions and enabled; the strategy and every exit
parameter live only in the gitignored database. A fresh install would start
eighteen symbols in exactly EURUSD's position.

opt_updated_at is the test rather than opt_summary, because that is the single
field apply() stamps when it writes a searched config.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _System:
    slippage_points = 20
    def to_dict(self): return {}


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, k, default=None): return default
    def opt_params(self): return {}
    def opt_history(self, s, n): return []

    def update_symbol(self, symbol, patch):
        cur = self.symbols[symbol].to_dict()
        for k, v in patch.items():
            if k in cur and v is not None:
                cur[k] = v
        self.symbols[symbol] = SymbolConfig.from_dict(cur)
        return self.symbols[symbol]


class _Client:
    connected = True
    def positions(self, magic=None, symbol=None): return []
    def set_overrides(self, m): pass
    def info(self, s): return None
    def resolve(self, s): return s
    def tick(self, s): return None


class _Engine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25
    def apply(self, *a, **k): return {"ok": True}


def _cfg(symbol, *, optimised, enabled=False, magic=1):
    c = SymbolConfig(symbol=symbol, magic=magic, enabled=enabled)
    if optimised:
        c.opt_updated_at = time.time()
        c.opt_score = 12.3
        c.strategy = "t3_flip"
        c.timeframe = "M30"
    return c


def _client(cfgs):
    store = _Store(cfgs)
    return TestClient(create_app(store, _Client(), _Engine(), _Optimizer())), store


# ------------------------------------------------------------- the refusal

def test_an_unsearched_symbol_cannot_be_switched_on():
    tc, store = _client([_cfg("EURUSD", optimised=False)])
    res = tc.post("/api/symbols/EURUSD", json={"enabled": True})
    assert res.status_code == 400
    assert "optimize edilmeden acilamaz" in res.text
    assert store.symbols["EURUSD"].enabled is False


def test_the_message_names_what_it_is_actually_carrying():
    """"t3_stoch/M5" is the default, and saying so is the whole point."""
    tc, _ = _client([_cfg("EURUSD", optimised=False)])
    body = tc.post("/api/symbols/EURUSD", json={"enabled": True}).text
    assert "EURUSD" in body
    assert "t3_stoch" in body and "M5" in body


def test_bulk_enable_is_refused_for_the_same_reason():
    """"Tumunu Ac" walks the whole book - the other door to the same write."""
    tc, store = _client([_cfg("GOOD", optimised=True, magic=1),
                         _cfg("EURUSD", optimised=False, magic=2)])
    res = tc.post("/api/symbols-bulk", json={"patch": {"enabled": True}})
    assert res.status_code == 400
    assert store.symbols["GOOD"].enabled is False, "kismi yazma olmus"
    assert store.symbols["EURUSD"].enabled is False


# --------------------------------------------------- what must keep working

def test_a_searched_symbol_switches_on_normally():
    tc, store = _client([_cfg("XAUUSD", optimised=True)])
    assert tc.post("/api/symbols/XAUUSD", json={"enabled": True}).status_code == 200
    assert store.symbols["XAUUSD"].enabled is True


def test_switching_OFF_is_never_blocked():
    """The safe direction must always be available, searched or not."""
    for optimised in (True, False):
        tc, store = _client([_cfg("X", optimised=optimised, enabled=True)])
        assert tc.post("/api/symbols/X", json={"enabled": False}).status_code == 200
        assert store.symbols["X"].enabled is False


def test_other_edits_to_an_unsearched_symbol_still_go_through():
    """Only enabling is gated - a session or ceiling change is fine."""
    tc, store = _client([_cfg("EURUSD", optimised=False)])
    res = tc.post("/api/symbols/EURUSD",
                  json={"sessions": [{"start": "01:00", "end": "23:55"}]})
    assert res.status_code == 200
    assert store.symbols["EURUSD"].sessions[0]["start"] == "01:00"


def test_bulk_enable_passes_when_every_target_is_searched():
    tc, store = _client([_cfg("A", optimised=True, magic=1),
                         _cfg("B", optimised=True, magic=2)])
    assert tc.post("/api/symbols-bulk", json={"patch": {"enabled": True}}).status_code == 200
    assert all(c.enabled for c in store.symbols.values())


def test_bulk_disable_is_never_blocked():
    tc, store = _client([_cfg("A", optimised=False, enabled=True, magic=1),
                         _cfg("B", optimised=False, enabled=True, magic=2)])
    assert tc.post("/api/symbols-bulk", json={"patch": {"enabled": False}}).status_code == 200
    assert not any(c.enabled for c in store.symbols.values())
