"""Current live values that the engine reads but cannot fire.

AUDIT-A asked 'is it read?'. This asks 'with tonight's numbers, can it
change a decision?'. cooldown_sec=120 is shorter than one bar of every
timeframe in the book, so a fill never delays the next bar. Six symbols
at 0.80% with EDGE_MAX 2.2 cannot reach a 15% concurrent-risk cap.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import _cooldown_for
from micofx.models import SymbolConfig
from micofx.mt5client import timeframe_seconds
from micofx.risk import RiskManager

LIVE_COOLDOWN_SEC = 120
LIVE_TIMEFRAMES = ("M5", "M15", "M30")
LIVE_N_SYMBOLS = 6
LIVE_RISK_PERCENT = 0.8
LIVE_CONCURRENT_RISK_PCT = 15.0


def test_cooldown_of_120s_expires_before_the_next_bar():
    """Bar-close entries; the pause is over before the next close exists."""
    for tf in LIVE_TIMEFRAMES:
        for strategy in ("t3_stoch", "burst", "stoch_flip"):
            cfg = SymbolConfig(symbol="GER40", timeframe=tf, strategy=strategy,
                               cooldown_sec=LIVE_COOLDOWN_SEC)
            pause = _cooldown_for(cfg)
            bar = timeframe_seconds(tf)
            assert pause < bar, (
                f"{strategy}/{tf}: cooldown {pause}s is not shorter than the "
                f"{bar}s bar, so it could finally block a later signal")


def test_six_symbols_at_edge_max_cannot_fill_the_concurrent_risk_cap():
    """size_by_edge clamp is 2.2; 6 * 0.80% * 2.2 = 10.56% < 15%."""
    ceiling = LIVE_N_SYMBOLS * LIVE_RISK_PERCENT * RiskManager.EDGE_MAX
    assert ceiling < LIVE_CONCURRENT_RISK_PCT, (
        f"book ceiling {ceiling}% reaches the {LIVE_CONCURRENT_RISK_PCT}% cap")
