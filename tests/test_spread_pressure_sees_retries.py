"""spread_pressure must see retry storms, not only unique block counts."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import spread_auto_targets
from micofx.entry_pressure import spread_pressure


def test_spread_pressure_uses_retries_when_blocks_thin():
    row = {
        "symbol": "US30",
        "signals": 8,
        "opened": 0,
        "fill_rate": 0.0,
        "blocks": {"seans_disi": 6, "spread": 2},
        "retries": {"spread": 879, "seans_disi": 6},
    }
    assert spread_pressure(row) == 17  # max(2, 879//50)
    assert spread_pressure({"blocks": {"spread": 20}}) == 20
    assert spread_pressure({}) == 0


def test_spread_auto_targets_sees_us30_retry_storm():
    rows = [
        {
            "symbol": "US30", "signals": 8, "opened": 0, "fill_rate": 0.0,
            "blocks": {"seans_disi": 6, "spread": 2},
            "retries": {"spread": 879},
        },
        {
            "symbol": "GER40", "signals": 30, "opened": 25, "fill_rate": 0.83,
            "blocks": {"spread": 1}, "retries": {"spread": 3},
        },
    ]
    assert spread_auto_targets(rows, open_symbols=set(), active={"US30", "GER40"}) == [
        "US30"
    ]
