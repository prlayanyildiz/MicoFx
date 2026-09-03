"""A newly shipped strategy-grid axis must reach a live stored blob."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.store import Store


def test_new_burst_trail_step_axis_backfills_onto_stored_family_grid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Isolate settings away from the live book.
    monkeypatch.setattr("micofx.store.DB_PATH", tmp_path / "opt.db")
    store = Store()
    store.defaults = {
        "optimizer": {
            "strategies": ["burst", "channel_break"],
            "strategy_grids": {
                "burst": {
                    "brst_lookback": [20],
                    "trail_step_atr": [0.6, 2.8, 3.2],
                },
            },
            "grid": {"trail_step_atr": [0.8, 2.2]},
        },
        "symbols": [],
        "group_presets": {},
        "system": {},
    }
    # Operator saved burst before trail_step existed on that family.
    store.set_setting("opt_params", {
        "strategy_grids": {
            "burst": {"brst_lookback": [10, 20]},
        },
    })
    merged = store.opt_params()
    burst = merged["strategy_grids"]["burst"]
    assert burst["brst_lookback"] == [10, 20]  # stored wins
    assert burst["trail_step_atr"] == [0.6, 2.8, 3.2]  # shipped-only back-fill


def test_shipped_grid_values_widen_a_stored_axis(tmp_path, monkeypatch):
    """Editing defaults.json must reach extra list values (channel_break 2.8)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("micofx.store.DB_PATH", tmp_path / "opt.db")
    store = Store()
    store.defaults = {
        "optimizer": {
            "strategies": ["channel_break"],
            "strategy_grids": {
                "channel_break": {"trail_step_atr": [0.4, 0.6, 2.2, 2.8]},
            },
            "grid": {"trail_step_atr": [0.8, 2.2, 2.8]},
        },
        "symbols": [],
        "group_presets": {},
        "system": {},
    }
    store.set_setting("opt_params", {
        "strategy_grids": {
            "channel_break": {"trail_step_atr": [0.4, 0.6, 2.2]},
        },
        "grid": {"trail_step_atr": [0.8, 2.2]},
    })
    merged = store.opt_params()
    assert 2.8 in merged["strategy_grids"]["channel_break"]["trail_step_atr"]
    assert 2.8 in merged["grid"]["trail_step_atr"]
    assert 0.4 in merged["strategy_grids"]["channel_break"]["trail_step_atr"]
