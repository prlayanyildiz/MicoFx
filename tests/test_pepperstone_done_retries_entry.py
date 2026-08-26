"""A Pepperstone 0/Done fill reported as a reject leaves the signal live.

Engine._try_entry only arms cooldown and the filled-bar lock on
``result["ok"]``. A DEAL that actually filled but came back
``emir reddedildi (0 Done)`` takes the emir_hatasi branch: no cooldown,
no _mark_bar_filled, pending_bar_key kept, next poll sends again.

retcode 0 is not in AMBIGUOUS_RETCODES and not NON_RETRYABLE, so this is
a plain retryable reject - not verified_unfilled, not a dropped signal.

The product fix is counting 0/Done as success in the client (then these
locks write themselves). Retry policy is not widened.
"""
from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig
from micofx.risk import Verdict


class _FakeClient:
    def __init__(self, open_result, positions_after=None):
        self._open_result = dict(open_result)
        self._positions_after = list(positions_after or [])
        self.open_market_calls = 0
        self.connected = True

    def min_stop_distance(self, symbol):
        return 0.0001

    def tick(self, symbol):
        return {"ask": 26482.2, "bid": 26481.6, "spread": 0.6}

    def open_market(self, symbol, side, lot, sl, tp, magic, slippage=0, comment="",
                    defer_verify=False):
        self.open_market_calls += 1
        out = dict(self._open_result)
        out.setdefault("requested", 26482.2)
        out.setdefault("price", 26482.2)
        out.setdefault("volume", lot)
        out.setdefault("sl", sl)
        out.setdefault("tp", tp)
        return out

    def positions(self):
        return list(self._positions_after)

    def info(self, symbol):
        return {"point": 0.1}

    def money_per_price_unit(self, symbol, volume):
        return 1.0


class _FakeRisk:
    def lot_for(self, cfg, sl_distance, balance, ai_scale=1.0):
        return 0.1, "ok"

    def can_open(self, cfg, side, lot, positions, account, sec_tickets=frozenset(), **_kw):
        return Verdict(ok=True)


class _FakeSupervisor:
    def gate(self, cfg, server_now):
        return True, "", 1.0


class _FakeExecution:
    def record(self, *a, **kw):
        pass


class _FakeSymbols:
    def __init__(self, cfg):
        self._cfg = cfg

    def get(self, symbol):
        return self._cfg

    def __iter__(self):
        yield self._cfg.symbol


class _FakeStore:
    def __init__(self, cfg):
        self.system = SimpleNamespace(slippage_points=5, block_high_cost=False,
                                       max_cost_pct_of_risk=0.0, trade_all_hours=True,
                                       daily_loss_flatten=False, day_end_flatten_min=0)
        self.symbols = _FakeSymbols(cfg)
        self.settings: dict = {}

    def opt_params(self):
        return {}

    def set_setting(self, key, value):
        self.settings[key] = value


def _make_engine(cfg, open_result, positions_after=None):
    client = _FakeClient(open_result, positions_after)
    store = _FakeStore(cfg)
    eng = object.__new__(Engine)
    eng.store = store
    eng.client = client
    eng.risk = _FakeRisk()
    eng.supervisor = _FakeSupervisor()
    eng.execution = _FakeExecution()
    eng.entry_lock = threading.Lock()
    eng._positions = []
    eng._sec_tickets = set()
    eng._sec_cfgs = {}
    eng._orphan_tickets = set()
    eng._orphan_scan = {}
    eng._link_backoff = {}
    eng._unfilled_probe = {}   # real Engine always has it
    eng.states = {}
    eng._cooldowns = {}
    eng._filled_bars = {}
    return eng, client, store


def _cfg():
    return SymbolConfig(symbol="GER40", group="crypto", magic=1, cooldown_sec=120)


def _state():
    st = SymbolState("GER40")
    st.signal = "buy"
    st.signal_source = "primary"
    st.primary_signal = "buy"
    st.atr = 20.0
    st.last_bar = 1_786_698_000
    st.pending_bar_key = ("primary", st.last_bar)
    return st


def test_false_reject_of_a_fill_retries_the_same_signal():
    """Live-shaped open_market refusal: retcode=0, not ambiguous, not parked."""
    reject = {
        "ok": False,
        "retcode": 0,
        "error": "GER40: emir reddedildi (0 Done)",
    }
    eng, client, _store = _make_engine(_cfg(), reject)
    state = _state()

    eng._try_entry(_cfg(), state, account={"balance": 1000.0})

    assert state.entry_block == "emir_hatasi"
    assert state.signal == "buy"
    assert state.pending_bar_key == ("primary", state.last_bar)
    assert state.cooldown_until == 0.0
    assert eng._filled_bars == {}
    assert "GER40" not in eng._link_backoff
    assert client.open_market_calls == 1

    eng._try_entry(_cfg(), state, account={"balance": 1000.0})
    assert client.open_market_calls == 2
    assert state.entry_block == "emir_hatasi"


def test_a_counted_fill_writes_cooldown_and_the_bar_lock():
    fill = {
        "ok": True,
        "position": 359585333,
        "partial_fill": False,
        "sl_tp_reanchored": True,
        "requested": 26482.2,
        "price": 26482.2,
        "volume": 0.1,
        "sl": 26462.2,
        "tp": 0.0,
    }
    eng, client, store = _make_engine(
        _cfg(), fill, positions_after=[{"ticket": 359585333, "magic": 1}],
    )
    state = _state()
    before = time.time()

    eng._try_entry(_cfg(), state, account={"balance": 1000.0})

    assert state.entry_block == "acildi"
    assert state.signal == ""
    assert state.cooldown_until >= before + 120
    assert store.settings.get("cooldowns") or store.settings
    assert eng._filled_bars.get("GER40", {}).get("primary") == state.last_bar
    assert client.open_market_calls == 1

    # Signal consumed; a second call in this test does not re-send because
    # _evaluate is what would re-offer. The locks above are what _evaluate
    # reads on the next poll / after a restart.
    calls = client.open_market_calls
    # Re-arm the signal the way a still-open bar would: filled-bar lock
    # must still refuse even if someone called _try_entry again after a
    # merge restored state.signal.
    state.signal = "buy"
    state.signal_source = "primary"
    # Direct _try_entry does not consult _filled_bars; _evaluate does.
    # Confirm the lock the cycle actually reads.
    assert eng._filled_bars["GER40"]["primary"] == 1_786_698_000
    assert calls == 1
