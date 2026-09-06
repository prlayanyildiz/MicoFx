"""Autopilot entry-block aggregate must keep retries for spread_pressure."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import _aggregate_entry_blocks, spread_auto_targets
from micofx.entry_pressure import spread_pressure


def test_aggregate_keeps_spread_retries():
    rows = [
        {
            "symbol": "US30", "signals": 4, "opened": 0,
            "blocks": {"spread": 1, "seans_disi": 3},
            "retries": {"spread": 400, "seans_disi": 3},
        },
        {
            "symbol": "US30", "signals": 4, "opened": 0,
            "blocks": {"spread": 1, "seans_disi": 3},
            "retries": {"spread": 479, "seans_disi": 3},
        },
    ]
    out = _aggregate_entry_blocks(rows)
    assert len(out) == 1
    row = out[0]
    assert row["signals"] == 8
    assert row["retries"]["spread"] == 879
    assert spread_pressure(row) == 17  # max(2, 879//50)


def test_spread_auto_targets_sees_retry_storm():
    rows = _aggregate_entry_blocks([{
        "symbol": "US30", "signals": 8, "opened": 0,
        "blocks": {"spread": 2, "seans_disi": 6},
        "retries": {"spread": 879},
    }])
    got = spread_auto_targets(rows, open_symbols=set(), active={"US30"})
    assert got == ["US30"]
