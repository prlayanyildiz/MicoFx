"""Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok.

A2: _merge_signals is primary-only. A primary BUY must survive a leftover
sec_signal SELL (the old disagreement skip cancelled both). Ticket/orphan
machinery is untouched.
"""
from __future__ import annotations

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig


def _eng():
    return object.__new__(Engine)


def test_merge_keeps_primary_buy_when_secondary_disagrees():
    eng = _eng()
    cfg = SymbolConfig(symbol="XAUUSD", ensemble_enabled=True,
                       secondary_strategy="micro_rev", secondary_timeframe="M5")
    state = SymbolState("XAUUSD")
    state.primary_signal = "buy"
    state.sec_signal = "sell"
    eng._merge_signals(cfg, state)
    assert state.signal == "buy"
    assert state.signal_source == "primary"


def test_merge_keeps_primary_buy_when_secondary_agrees():
    """Same-direction secondary must not steal the source tag either."""
    eng = _eng()
    cfg = SymbolConfig(symbol="XAUUSD", ensemble_enabled=True,
                       secondary_strategy="burst", secondary_timeframe="M5")
    state = SymbolState("XAUUSD")
    state.primary_signal = "buy"
    state.sec_signal = "buy"
    eng._merge_signals(cfg, state)
    assert state.signal == "buy"
    assert state.signal_source == "primary"


def test_merge_empty_primary_does_not_promote_secondary():
    eng = _eng()
    cfg = SymbolConfig(symbol="XAUUSD", ensemble_enabled=True,
                       secondary_strategy="burst", secondary_timeframe="M5")
    state = SymbolState("XAUUSD")
    state.primary_signal = ""
    state.sec_signal = "sell"
    eng._merge_signals(cfg, state)
    assert state.signal == ""
    assert state.signal_source == ""
