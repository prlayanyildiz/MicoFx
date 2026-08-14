"""Hard-scan fixes: enabled=False /must not freeze
management of an already-open position.

Both bugs share one root cause: manage_positions()'s trail/BE/partial-TP
throttle only fires _update_stop() when state.last_bar (or sec_last_bar)
actually advances. Two ordinary, UI-reachable config actions used to stop
that advancement for a ticket that stays open and tracked:

  - cfg.enabled = False (pause a symbol) skipped _evaluate() entirely, so
    state.last_bar/atr froze at whatever they were the instant it was
    disabled.
  -(or secondary_strategy cleared) with a
    secondary-opened ticket still live: state.sec_last_bar/sec_bars were
    reset and state.sec_atr was left stale-but-still-positive, so
    manage_positions() neither swapped to primary management nor kept
    trailing on the secondary view - it just silently stopped updating.

Neither used to log or flag the position as unmanaged; only the broker's own
static SL/TP kept protecting it.
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig


class _FakeStore:
    def __init__(self):
        self.settings: dict = {}


def _make_engine(cfg):
    eng = object.__new__(Engine)
    eng.store = _FakeStore()
    eng.client = SimpleNamespace(connected=True)
    eng.entry_lock = threading.Lock()
    eng._positions = []
    eng._sec_tickets = set()
    eng.states = {}
    return eng


def _cfg(**over):
    base = dict(symbol="EURUSD", group="crypto", magic=1, enabled=False)
    base.update(over)
    return SymbolConfig(**base)


# ------------------------------------------------------- _evaluate_disabled

def test_evaluate_disabled_keeps_refreshing_when_position_still_open():
    cfg = _cfg()
    eng = _make_engine(cfg)
    eng._positions = [{"ticket": 1, "magic": cfg.magic, "side": "buy", "volume": 0.1,
                       "time": 0, "profit": 0, "swap": 0}]
    state = SymbolState(cfg.symbol)
    state.primary_signal = "buy"  # would look "stale" under the old clear-on-disable path

    calls = []

    def _fake_evaluate(cfg_arg, state_arg, server_now, account, allow_entry):
        calls.append((cfg_arg, state_arg, server_now, account, allow_entry))
        state_arg.last_bar = 999  # simulates a real bar-close refresh happening

    eng._evaluate = _fake_evaluate

    eng._evaluate_disabled(cfg, state, server_now=123.0, account={"equity": 100.0})

    assert len(calls) == 1
    assert calls[0][4] is False  # allow_entry must be False - never arms a new entry
    assert state.last_bar == 999  # bar tracking actually advanced
    assert state.note == "kapali"
    # NOT cleared - _evaluate() itself owns the signal chain now that it runs
    assert state.primary_signal == "buy"


def test_evaluate_disabled_clears_signal_chain_when_no_position_open():
    cfg = _cfg()
    eng = _make_engine(cfg)
    eng._positions = []  # no position under this magic
    state = SymbolState(cfg.symbol)
    state.primary_signal = "buy"
    state.signal = "buy"
    state.signal_source = "primary"
    state.pending_bar_key = ("primary", 555)

    calls = []
    eng._evaluate = lambda *a, **kw: calls.append(a)

    eng._evaluate_disabled(cfg, state, server_now=123.0, account={"equity": 100.0})

    assert calls == []  # no reason to poll the broker for a flat, disabled symbol
    assert state.note == "kapali"
    assert state.signal == ""
    assert state.signal_source == ""
    assert state.primary_signal == ""
    assert state.pending_bar_key == (0, 0)


def test_evaluate_disabled_swallows_evaluate_exception():
    cfg = _cfg()
    eng = _make_engine(cfg)
    eng._positions = [{"ticket": 1, "magic": cfg.magic, "side": "buy", "volume": 0.1,
                       "time": 0, "profit": 0, "swap": 0}]
    state = SymbolState(cfg.symbol)

    def _boom(*a, **kw):
        raise RuntimeError("broker hiccup")

    eng._evaluate = _boom

    # Must not raise - this runs inside the main per-cycle symbol loop, and a
    # crash here must not take out every OTHER symbol's evaluation this cycle.
    eng._evaluate_disabled(cfg, state, server_now=123.0, account={"equity": 100.0})
    assert state.note == "kapali"


# ------------------------------------------ _evaluate(): leftover ticket, A2

def test_has_open_secondary_ticket_helper_is_gone():
    """Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok.

    The helper had no remaining callers after A2; leftover tags still live in
    ``_sec_tickets`` for prune/web guards (A3.3 readers stay).
    """
    assert not hasattr(Engine, "_has_open_secondary_ticket")

def test_evaluate_still_refreshes_primary_when_leftover_ticket_is_open(monkeypatch):
    """A tagged leftover ticket must keep primary last_bar/atr advancing so
    manage_positions does not freeze. Overlay refresh is gone (A2).
    """
    from micofx import sessions as sessions_mod

    cfg = _cfg(enabled=True,)
    eng = _make_engine(cfg)
    eng.client.resolve = lambda symbol: symbol
    eng.client.tick = lambda symbol: None
    eng.client.market_open = lambda symbol: True
    eng.store.system = SimpleNamespace(trade_all_hours=True)
    eng._sec_tickets = {77}
    eng._positions = [{"ticket": 77, "magic": cfg.magic, "side": "buy", "volume": 0.1,
                       "time": 0, "profit": 0, "swap": 0}]

    open_session = SimpleNamespace(open=True, reason="", minutes_to_close=None,
                                   minutes_to_open=None, window="24/7")
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: open_session)

    refresh_calls = []

    def _fake_refresh(cfg_arg, state_arg, params):
        refresh_calls.append(cfg_arg)
        state_arg.atr = 0.0042
        state_arg.last_bar = 12345
        return True

    eng._refresh_signals = _fake_refresh

    state = SymbolState(cfg.symbol)
    eng._evaluate(cfg, state, server_now=1000.0, account={"equity": 100.0}, allow_entry=False)

    assert refresh_calls == [cfg]
    assert state.atr == 0.0042
    assert state.last_bar == 12345
    assert not hasattr(Engine, "_refresh_secondary")
    assert not hasattr(Engine, "_secondary_config")


def test_evaluate_has_no_secondary_refresh_when_ensemble_is_on(monkeypatch):
    """Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok.

    has_secondary() used to fetch a second bar stream every cycle. That
    production path is gone; leftover ticket tagging is A3 and still exists.
    """
    from micofx import sessions as sessions_mod

    cfg = _cfg(enabled=True)
    assert not hasattr(cfg, "has_secondary")
    eng = _make_engine(cfg)
    eng.client.resolve = lambda symbol: symbol
    eng.client.tick = lambda symbol: None
    eng.client.market_open = lambda symbol: True
    eng.store.system = SimpleNamespace(trade_all_hours=True)
    eng._sec_tickets = set()
    eng._positions = []

    open_session = SimpleNamespace(open=True, reason="", minutes_to_close=None,
                                   minutes_to_open=None, window="24/7")
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: open_session)
    eng._refresh_signals = lambda cfg_arg, state_arg, params: False

    state = SymbolState(cfg.symbol)
    eng._evaluate(cfg, state, server_now=1000.0, account={"equity": 100.0}, allow_entry=False)

    assert not hasattr(eng, "_refresh_secondary")
    assert not hasattr(Engine, "_refresh_secondary")

