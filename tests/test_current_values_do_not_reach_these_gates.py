"""Current live values that the engine reads but cannot fire.

AUDIT-A asked 'is it read?'. This asks 'with tonight's numbers, can it
change a decision?'. cooldown_sec=120 is shorter than one bar of every
timeframe in the book, so a fill never delays the next bar.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import _cooldown_for
from micofx.models import SymbolConfig
from micofx.mt5client import timeframe_seconds

LIVE_COOLDOWN_SEC = 120
LIVE_TIMEFRAMES = ("M5", "M15", "M30")


def test_cooldown_of_120s_expires_before_the_next_bar():
    """Bar-close entries; the pause is over before the next close exists."""
    for tf in LIVE_TIMEFRAMES:
        for strategy in ("dual_t3", "burst", "stoch_flip"):
            cfg = SymbolConfig(symbol="GER40", timeframe=tf, strategy=strategy,
                               cooldown_sec=LIVE_COOLDOWN_SEC)
            pause = _cooldown_for(cfg)
            bar = timeframe_seconds(tf)
            assert pause < bar, (
                f"{strategy}/{tf}: cooldown {pause}s is not shorter than the "
                f"{bar}s bar, so it could finally block a later signal")
