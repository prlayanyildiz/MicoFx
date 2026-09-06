"""Live chase ceiling: tick vs signal close in ATR units (Antigravity FAZ4).

Distinct from the autopsy R-threshold curve-fit AGENTS used to ban: this
gates on adverse price distance / ATR before order_send. 0 = off.
"""
from __future__ import annotations

from scripts.chase_r_log import chase_blocks, fill_vs_signal


def test_fill_vs_signal_sign():
    assert fill_vs_signal(101.0, 100.0, "buy") == 1.0
    assert fill_vs_signal(99.0, 100.0, "sell") == 1.0
    assert fill_vs_signal(100.0, 100.0, "buy") == 0.0


def test_chase_blocks_when_adverse_exceeds_atr_cap():
    # buy 0.3 ATR adverse vs cap 0.25 → block
    assert chase_blocks(100.3, 100.0, "buy", atr=1.0, max_atr=0.25)
    assert not chase_blocks(100.2, 100.0, "buy", atr=1.0, max_atr=0.25)
    assert not chase_blocks(100.5, 100.0, "buy", atr=1.0, max_atr=0.0)  # off
    assert chase_blocks(99.7, 100.0, "sell", atr=1.0, max_atr=0.25)
    assert not chase_blocks(99.8, 100.0, "sell", atr=1.0, max_atr=0.25)
