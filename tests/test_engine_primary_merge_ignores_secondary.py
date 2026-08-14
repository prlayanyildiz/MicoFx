"""Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok.

A2: _merge_signals is primary-only. A primary BUY stays BUY; an empty
primary cannot be promoted. Ticket/orphan machinery is untouched.
"""
from __future__ import annotations

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig


def _eng():
    return object.__new__(Engine)


def test_merge_keeps_primary_buy():
    eng = _eng()
    cfg = SymbolConfig(symbol="XAUUSD",)
    state = SymbolState("XAUUSD")
    state.primary_signal = "buy"
    eng._merge_signals(cfg, state)
    assert state.signal == "buy"
    assert state.signal_source == "primary"
    assert not hasattr(state, "sec_signal")


def test_merge_empty_primary_stays_empty():
    eng = _eng()
    cfg = SymbolConfig(symbol="XAUUSD",)
    state = SymbolState("XAUUSD")
    state.primary_signal = ""
    eng._merge_signals(cfg, state)
    assert state.signal == ""
    assert state.signal_source == ""
