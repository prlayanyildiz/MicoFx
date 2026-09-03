"""Short grid axes (adx_min, max_spread_atr) must appear in a sampled search.

Claude 03.09: US30 adx 0->20 was +43R to +85R, but WFO 'does not search adx'
was sampling luck — shipped grid already has [0, 15, 20] and the 2000-combo
draw can miss a 3-value axis. Same hole for msa 0.04 after it is on the list.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.backtest import combos_from_grid


def test_sampled_search_covers_every_adx_min_value():
    grid = {
        "adx_min": [0.0, 15.0, 20.0],
        "sl_atr_mult": [1.0, 1.5, 2.0, 2.5, 3.0],
        "trail_start_atr": [0.3, 0.5, 0.8, 1.2, 2.0],
        "trail_step_atr": [0.6, 0.8, 1.2, 1.6, 2.2, 2.8],
        "chan_lookback": [20, 40, 60, 100, 150],
        "htf_factor": [0, 3, 6],
        "max_spread_atr": [0.04, 0.05, 0.08, 0.12, 0.18],
    }
    keys, combos = combos_from_grid(grid, max_combos=6, seed=16)
    assert len(combos) <= 6
    adx_i = keys.index("adx_min")
    seen = {combos[j][adx_i] for j in range(len(combos))}
    assert seen == {0, 1, 2}


def test_sampled_search_covers_msa_floor_004():
    grid = {
        "adx_min": [0.0, 15.0, 20.0],
        "max_spread_atr": [0.04, 0.05, 0.08, 0.12, 0.18],
        "pull_fast": [5, 8, 13, 21],
        "pull_depth_atr": [0.3, 0.5, 0.8, 1.2],
        "pull_max_bars": [4, 6, 10],
        "htf_factor": [3, 6, 12],
        "sl_atr_mult": [1.0, 1.5, 2.0, 2.5, 3.0],
        "trail_start_atr": [0.5, 1.0, 1.5, 2.0],
        "trail_step_atr": [0.4, 0.8, 1.2, 2.2],
    }
    keys, combos = combos_from_grid(grid, max_combos=25, seed=137)
    msa_i = keys.index("max_spread_atr")
    seen = {combos[j][msa_i] for j in range(len(combos))}
    assert 0 in seen, "msa 0.04 must be in the sample"
    assert seen == set(range(5))
