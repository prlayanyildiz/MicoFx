"""Deferred fill must book the send-time bar, not whatever is live 2s later.

Cycle order is evaluate → drain → entries. A pending_verify sleeps off-thread
while the engine keeps cycling, so drain can run after bar T+1 has already
armed a new signal. Booking used live ``state.signal_source`` / ``last_bar``:

* a rolled bar's new signal was cleared → that entry never fired
* if live source was already "" the filled-bar key landed under "" while
  live entries key ``primary`` → same bar re-entered after restart

The pending blob now carries the send-time source and bar. Drain marks those
and only clears the live chain when last_bar is still the filled one.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig

BAR_T = 1_786_400_000
BAR_T1 = BAR_T + 1800


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
        self.saved = {}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)

    def set_setting(self, key, value):
        self.saved[key] = value


class _Client:
    def info(self, _symbol):
        return {"point": 0.01}

    def money_per_price_unit(self, _symbol, _vol):
        return 1.0

    def broker_now(self):
        return float(BAR_T1)


class _Exec:
    def __init__(self):
        self.fills = []

    def record(self, *a, **k):
        return None

    def note_fill(self, ticket, **kw):
        self.fills.append((ticket, kw))


def _engine(cfg):
    eng = object.__new__(Engine)
    eng.store = _Store(cfg)
    eng.client = _Client()
    eng.execution = _Exec()
    eng.states = {}
    eng._filled_bars = {}
    eng._cooldowns = {}
    return eng


def _pending(source="primary", bar=BAR_T):
    return {
        "symbol": "NAS100",
        "side": "buy",
        "sl_dist": 50.0,
        "lot": 0.2,
        "entry": 29100.0,
        "note": "",
        "tick": {"spread": 1.0},
        "signal_source": source,
        "bar_key": (bar, bar),
        "last_bar": bar,
    }


def test_a_newer_bar_signal_survives_the_deferred_fill():
    cfg = SymbolConfig(symbol="NAS100", magic=1, timeframe="M30", cooldown_sec=120)
    eng = _engine(cfg)
    state = SymbolState("NAS100")
    state.last_bar = BAR_T1
    state.signal = "buy"
    state.signal_source = "primary"
    state.primary_signal = "buy"
    state.atr = 60.0
    eng.states["NAS100"] = state

    eng._book_deferred_fill(
        cfg, state,
        {"ok": True, "price": 29110.0, "volume": 0.2, "position": 42,
         "requested": 29100.0, "sl": 29060.0, "tp": 0.0},
        _pending(),
    )

    assert eng._filled_bars["NAS100"]["primary"] == BAR_T
    assert state.signal == "buy", "T+1 signal was wiped with the fill of T"
    assert state.signal_source == "primary"
    assert state.last_bar == BAR_T1
    assert eng.execution.fills[0][1]["signal_bar_time"] == BAR_T


def test_the_same_bar_is_still_consumed():
    cfg = SymbolConfig(symbol="NAS100", magic=1, timeframe="M30", cooldown_sec=120)
    eng = _engine(cfg)
    state = SymbolState("NAS100")
    state.last_bar = BAR_T
    state.signal = "buy"
    state.signal_source = "primary"
    state.primary_signal = "buy"
    eng.states["NAS100"] = state

    eng._book_deferred_fill(
        cfg, state,
        {"ok": True, "price": 29110.0, "volume": 0.2, "position": 42,
         "requested": 29100.0, "sl": 29060.0, "tp": 0.0},
        _pending(),
    )

    assert eng._filled_bars["NAS100"]["primary"] == BAR_T
    assert state.signal == ""
    assert state.signal_source == ""


def test_deferred_fill_pins_signal_close_to_booked_bar_not_live_last():
    """Verifier sleep across a bar close must not use T+1 close for chase/R."""
    from types import SimpleNamespace
    from micofx.engine import _signal_close_for_bar

    bars = SimpleNamespace(
        time=[BAR_T, BAR_T1],
        close=[29100.0, 29200.0],
    )
    assert _signal_close_for_bar(bars, BAR_T) == 29100.0
    assert _signal_close_for_bar(bars, BAR_T1) == 29200.0
    assert _signal_close_for_bar(bars, 0) == 29200.0

    cfg = SymbolConfig(symbol="NAS100", magic=1, timeframe="M30", cooldown_sec=120)
    eng = _engine(cfg)
    state = SymbolState("NAS100")
    state.last_bar = BAR_T1
    state.bars = bars
    state.atr = 60.0
    eng.states["NAS100"] = state

    eng._book_deferred_fill(
        cfg, state,
        {"ok": True, "price": 29110.0, "volume": 0.2, "position": 42,
         "requested": 29100.0, "sl": 29060.0, "tp": 0.0},
        _pending(bar=BAR_T),
    )
    assert eng.execution.fills[0][1]["signal_close"] == 29100.0
    assert eng.execution.fills[0][1]["signal_bar_time"] == BAR_T
