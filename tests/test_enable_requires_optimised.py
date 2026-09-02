"""A symbol may not be switched on until the optimizer has chosen its config.

EURUSD reached ``enabled`` carrying nothing but the dataclass defaults -
opt_updated_at 0.0, opt_score 0.0, an empty opt_summary and stoch_flip/M5. That
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

    def update_symbol(self, symbol, patch, source=""):
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


class _Supervisor:
    def update_settings(self, body):
        return body

    def clear(self, symbol=None):
        pass


class _Engine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}
        self.supervisor = _Supervisor()


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25
    def apply(self, *a, **k): return {"ok": True}


def _cfg(symbol, *, optimised, enabled=False, magic=1):
    c = SymbolConfig(symbol=symbol, magic=magic, enabled=enabled)
    if optimised:
        c.opt_updated_at = time.time()
        c.opt_score = 12.3
        c.strategy = "channel_break"
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
    """"mtf_pullback/M5" is the default, and saying so is the whole point."""
    tc, _ = _client([_cfg("EURUSD", optimised=False)])
    body = tc.post("/api/symbols/EURUSD", json={"enabled": True}).text
    assert "EURUSD" in body
    assert "mtf_pullback" in body and "M5" in body


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


# ------------------------------- rule 2: a config priced too cheaply for reality

class _Opt(_Optimizer):
    def __init__(self, scales=None):
        self.scales = scales or {}

    def _spread_scale(self, symbol):
        return self.scales.get(symbol, 1.0)


def _cfg_scaled(symbol, *, stamped, magic=1, enabled=False):
    c = _cfg(symbol, optimised=True, enabled=enabled, magic=magic)
    summary = {"holdout": {"score": 9.0}}
    if stamped is not None:
        summary["spread_scale"] = stamped
    c.opt_summary = summary
    return c


def _client_scaled(cfgs, scales):
    store = _Store(cfgs)
    return TestClient(create_app(store, _Client(), _Engine(), _Opt(scales))), store


def test_a_config_selected_cheaper_than_reality_cannot_be_switched_on():
    """EURJPY: stamped nothing (so 1.0), measured 1.75. Its recalibrated
    candidate was refused by an absolute gate, so the stored config is the
    pre-calibration one, selected at 57% of the measured spread."""
    tc, store = _client_scaled([_cfg_scaled("EURJPY", stamped=None)],
                               {"EURJPY": 1.75})
    res = tc.post("/api/symbols/EURJPY", json={"enabled": True})
    assert res.status_code == 400
    assert "ucuza secilmis" in res.text
    assert store.symbols["EURJPY"].enabled is False


def test_the_message_states_both_numbers():
    tc, _ = _client_scaled([_cfg_scaled("EURJPY", stamped=None)], {"EURJPY": 1.75})
    body = tc.post("/api/symbols/EURJPY", json={"enabled": True}).text
    assert "1.00x" in body and "1.75x" in body


def test_a_config_selected_MORE_expensively_is_still_enableable():
    """CHFJPY stamped 3.35 and measures 3.05 an hour later. Selected against a
    harsher cost than reality is conservative - and the histogram keeps moving,
    so a symmetric check would refuse symbols over ordinary safe drift."""
    tc, store = _client_scaled([_cfg_scaled("CHFJPY", stamped=3.35)],
                               {"CHFJPY": 3.05})
    assert tc.post("/api/symbols/CHFJPY", json={"enabled": True}).status_code == 200
    assert store.symbols["CHFJPY"].enabled is True


@pytest.mark.parametrize("stamped,measured", [(1.0, 1.05), (None, 1.05), (1.15, 1.15)])
def test_ordinary_drift_does_not_block(stamped, measured):
    tc, store = _client_scaled([_cfg_scaled("X", stamped=stamped)], {"X": measured})
    assert tc.post("/api/symbols/X", json={"enabled": True}).status_code == 200


def test_a_freshly_stamped_config_is_enableable_at_its_own_scale():
    """Self-clearing: a new search stamps the current scale."""
    tc, _ = _client_scaled([_cfg_scaled("XAUUSD", stamped=1.15)], {"XAUUSD": 1.15})
    assert tc.post("/api/symbols/XAUUSD", json={"enabled": True}).status_code == 200


def test_switching_off_is_still_never_blocked():
    tc, store = _client_scaled([_cfg_scaled("EURJPY", stamped=None, enabled=True)],
                               {"EURJPY": 1.75})
    assert tc.post("/api/symbols/EURJPY", json={"enabled": False}).status_code == 200
    assert store.symbols["EURJPY"].enabled is False


def test_bulk_enable_is_refused_for_a_stale_cost_basis_too():
    tc, store = _client_scaled(
        [_cfg_scaled("GOOD", stamped=1.0, magic=1),
         _cfg_scaled("EURJPY", stamped=None, magic=2)],
        {"GOOD": 1.0, "EURJPY": 1.75})
    assert tc.post("/api/symbols-bulk", json={"patch": {"enabled": True}}).status_code == 400
    assert store.symbols["GOOD"].enabled is False, "kismi yazma olmus"


def test_a_missing_optimizer_never_blocks():
    """create_app is called with optimizer=None in places; it must degrade."""
    store = _Store([_cfg_scaled("X", stamped=None)])
    tc = TestClient(create_app(store, _Client(), _Engine(), optimizer=None))
    assert tc.post("/api/symbols/X", json={"enabled": True}).status_code == 200
