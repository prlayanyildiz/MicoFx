"""channel_break must not fall through to the scalp-tight generic spread axis.

US30 WFO picked max_spread_atr=0.02 from the shared grid (0.01/0.02/…)
because channel_break's strategy_grid omitted the axis. M30 swing then
blocked every London/NY fill on a 1–3 pt CFD quote.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = json.loads(
    (ROOT / "config" / "defaults.json").read_text(encoding="utf-8"))


def test_channel_break_ships_its_own_max_spread_axis():
    grids = DEFAULTS["optimizer"]["strategy_grids"]
    assert "max_spread_atr" in grids["channel_break"]
    assert grids["channel_break"]["max_spread_atr"] == [0.05, 0.08, 0.12, 0.18]


def test_burst_also_ships_max_spread_so_families_stay_aligned():
    grids = DEFAULTS["optimizer"]["strategy_grids"]
    assert grids["burst"]["max_spread_atr"] == [0.05, 0.08, 0.12, 0.18]


def test_generic_scalp_tight_values_are_not_on_channel_break():
    vals = DEFAULTS["optimizer"]["strategy_grids"]["channel_break"]["max_spread_atr"]
    assert 0.01 not in vals and 0.02 not in vals
