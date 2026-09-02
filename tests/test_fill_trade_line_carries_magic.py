"""The fill TRADE line has to name which magic opened, and what cost/R was.

JPN225 #364015065 on 24.08 could not be verified as ours: the TRADE line
carries ticket, side, lot, price, SL, TP and the lot-note, and never the
magic. /api/state is 401 without the session cookie, so the log was the
only disk record and it was missing the one field that distinguishes this
engine's fill from a hand ticket.

The same line never said how close the fill was to the 18% cost gate.
``entry_blocks`` has never grown a ``maliyet`` key since 16.08; without
the percentage on the fills that *passed*, that zero cannot tell a live
regime under the cap from a gate that is not computing.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_the_fill_trade_line_names_magic_and_live_cost_share():
    src = (ROOT / "micofx" / "engine.py").read_text(encoding="utf-8")
    start = src.index("cost_bit = ")
    chunk = src[start:start + 1400]
    assert "magic={cfg.magic}" in chunk, chunk
    assert "maliyet %" in chunk, chunk
    assert '"TRADE"' in chunk
