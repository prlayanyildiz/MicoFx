"""Hard-scan fixes: enabled=False / ensemble_enabled=False must not freeze
management of an already-open position.

Both bugs share one root cause: manage_positions()'s trail/BE/partial-TP
throttle only fires _update_stop() when state.last_bar (or sec_last_bar)
actually advances. Two ordinary, UI-reachable config actions used to stop
that advancement for a ticket that stays open and tracked:

  - cfg.enabled = False (pause a symbol) skipped _evaluate() entirely, so
    state.last_bar/atr froze at whatever they were the instant it was
    disabled.
  - ensemble_enabled = False (or secondary_strategy cleared) with a
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


# --------------------------------------------------- _has_open_secondary_ticket

def test_has_open_secondary_ticket_true_for_matching_magic_and_tagged_ticket():
    cfg = _cfg(enabled=True)
    eng = _make_engine(cfg)
    eng._sec_tickets = {42}
    eng._positions = [{"ticket": 42, "magic": cfg.magic, "side": "buy", "volume": 0.1,
                       "time": 0, "profit": 0, "swap": 0}]
    assert eng._has_open_secondary_ticket(cfg) is True


def test_has_open_secondary_ticket_false_when_ticket_untagged():
    cfg = _cfg(enabled=True)
    eng = _make_engine(cfg)
    eng._sec_tickets = set()
    eng._positions = [{"ticket": 42, "magic": cfg.magic, "side": "buy", "volume": 0.1,
                       "time": 0, "profit": 0, "swap": 0}]
    assert eng._has_open_secondary_ticket(cfg) is False


def test_has_open_secondary_ticket_false_when_no_position_open():
    cfg = _cfg(enabled=True)
    eng = _make_engine(cfg)
    eng._sec_tickets = {42}
    eng._positions = []
    assert eng._has_open_secondary_ticket(cfg) is False


def test_has_open_secondary_ticket_ignores_other_magics():
    cfg = _cfg(enabled=True, magic=1)
    eng = _make_engine(cfg)
    eng._sec_tickets = {42}
    eng._positions = [{"ticket": 42, "magic": 999, "side": "buy", "volume": 0.1,
                       "time": 0, "profit": 0, "swap": 0}]
    assert eng._has_open_secondary_ticket(cfg) is False


# ------------------------------------------ _evaluate(): ensemble toggled off

def test_evaluate_keeps_refreshing_secondary_when_ensemble_off_with_open_ticket(monkeypatch):
    """ensemble_enabled=False (secondary_strategy still set) with a live
    secondary-tagged ticket must keep state.sec_atr/sec_last_bar advancing -
    not reset them - so manage_positions()'s per-bar throttle does not freeze.
    """
    from micofx import sessions as sessions_mod

    cfg = _cfg(enabled=True, ensemble_enabled=False,
              secondary_strategy="micro_rev", secondary_timeframe="M5")
    assert cfg.has_secondary() is False  # ensemble_enabled gates it off

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

    eng._refresh_signals = lambda cfg_arg, state_arg, params: False
    sec_refresh_calls = []

    def _fake_refresh_secondary(cfg_arg, state_arg):
        sec_refresh_calls.append(cfg_arg)
        state_arg.sec_atr = 0.0042
        state_arg.sec_last_bar = 12345
        return True

    eng._refresh_secondary = _fake_refresh_secondary

    state = SymbolState(cfg.symbol)
    state.sec_atr = 0.0042  # already had a valid ATR from before the toggle

    eng._evaluate(cfg, state, server_now=1000.0, account={"equity": 100.0}, allow_entry=False)

    assert sec_refresh_calls == [cfg]  # kept refreshing, not skipped
    assert state.sec_atr == 0.0042     # not reset to 0.0
    assert state.sec_last_bar == 12345  # bar tracking advanced


def test_evaluate_resets_secondary_state_when_no_open_ticket_and_ensemble_off(monkeypatch):
    """Same ensemble-off config, but with NO open secondary ticket - this is
    the ordinary case (ensemble genuinely turned off, nothing to protect) and
    must still fully clear/reset, exactly like before this fix.
    """
    from micofx import sessions as sessions_mod

    cfg = _cfg(enabled=True, ensemble_enabled=False,
              secondary_strategy="micro_rev", secondary_timeframe="M5")
    eng = _make_engine(cfg)
    eng.client.resolve = lambda symbol: symbol
    eng.client.tick = lambda symbol: None
    eng.client.market_open = lambda symbol: True
    eng.store.system = SimpleNamespace(trade_all_hours=True)
    eng._sec_tickets = set()
    eng._positions = []  # nothing open under this magic at all

    open_session = SimpleNamespace(open=True, reason="", minutes_to_close=None,
                                   minutes_to_open=None, window="24/7")
    monkeypatch.setattr(sessions_mod, "evaluate", lambda *a, **kw: open_session)
    eng._refresh_signals = lambda cfg_arg, state_arg, params: False

    def _should_not_be_called(cfg_arg, state_arg):
        raise AssertionError("_refresh_secondary must not run with no open ticket")

    eng._refresh_secondary = _should_not_be_called

    state = SymbolState(cfg.symbol)
    state.sec_atr = 0.0042
    state.sec_signal = "buy"
    state.sec_last_bar = 999

    eng._evaluate(cfg, state, server_now=1000.0, account={"equity": 100.0}, allow_entry=False)

    assert state.sec_atr == 0.0
    assert state.sec_signal == ""
    assert state.sec_last_bar == 0
    assert state.sec_bars is None


def test_evaluate_does_not_refresh_secondary_just_because_ensemble_is_on(monkeypatch):
    """Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok.

    has_secondary() used to fetch a second bar stream every cycle to arm
    entries. With no leftover tagged ticket that refresh is production, not
    management, and must not run.
    """
    from micofx import sessions as sessions_mod

    cfg = _cfg(enabled=True, ensemble_enabled=True,
              secondary_strategy="micro_rev", secondary_timeframe="M5")
    assert cfg.has_secondary() is True
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

    def _should_not_be_called(cfg_arg, state_arg):
        raise AssertionError("_refresh_secondary must not run with no open ticket")

    eng._refresh_secondary = _should_not_be_called

    state = SymbolState(cfg.symbol)
    eng._evaluate(cfg, state, server_now=1000.0, account={"equity": 100.0}, allow_entry=False)

