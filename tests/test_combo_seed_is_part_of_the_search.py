"""The search's RNG seed must be a recorded parameter, not a parent-process patch.

``combos_from_grid`` samples with numpy when the grid is larger than the
budget. That call used to hard-code seed 7 inside ``walk_forward``, and
``_sweep_worker`` runs in a spawned process — a monkeypatch on the parent
never reached it. D1b's seed repeats therefore measured a bar-window shift,
not seed noise.

Default stays 7 so live searches do not move. The seed travels in the job
dict (pickleable) and lands on the opt stamp next to coverage.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_apply_without_detail_stamp import NEW, _opt

from micofx.backtest import combos_from_grid, walk_forward
from micofx.optimizer import _sweep_worker

# 8^5 = 32768, well above a 2000 budget, so sampling (not the full product) runs.
_GRID = {f"axis_{i}": list(range(8)) for i in range(5)}
_BUDGET = 2000


def test_the_same_seed_draws_the_same_sample():
    _, a = combos_from_grid(_GRID, _BUDGET, seed=7)
    _, b = combos_from_grid(_GRID, _BUDGET, seed=7)
    assert a == b
    _, c = combos_from_grid(_GRID, _BUDGET)
    assert c == a, "omitted seed must keep the live default of 7"


def test_a_different_seed_draws_a_different_sample():
    _, a = combos_from_grid(_GRID, _BUDGET, seed=7)
    _, b = combos_from_grid(_GRID, _BUDGET, seed=11)
    assert a != b
    assert len(a) == len(b) == _BUDGET


def test_a_grid_that_fits_the_budget_ignores_the_seed():
    """Full Cartesian product: there is nothing to sample."""
    tiny = {"a": [1, 2], "b": [3, 4, 5]}
    _, a = combos_from_grid(tiny, 2000, seed=7)
    _, b = combos_from_grid(tiny, 2000, seed=11)
    assert a == b
    assert len(a) == 6


def test_walk_forward_hands_combo_seed_to_the_sampler():
    src = inspect.getsource(walk_forward)
    assert "combo_seed" in src
    assert "combos_from_grid(grid, max_combos, seed=combo_seed)" in src, (
        "walk_forward must pass combo_seed through, not hard-code 7"
    )


def test_the_worker_reads_combo_seed_from_the_job_dict():
    """ProcessPoolExecutor pickle-sends the job. A parent monkeypatch dies here."""
    src = inspect.getsource(_sweep_worker)
    assert "combo_seed" in src
    assert "payload" in src and "combo_seed" in src
    # The value has to go into walk_forward, not just be mentioned.
    assert "combo_seed=" in src


def test_old_stamp_without_combo_seed_still_applies():
    opt, _store, cfg = _opt()
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=NEW)
    assert result["ok"] is True, result
    assert (cfg.opt_summary or {}).get("combo_seed") is None


def test_new_apply_writes_combo_seed_from_detail():
    opt, _store, cfg = _opt()
    detail = dict(NEW)
    detail["combo_seed"] = 11
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=detail)
    assert result["ok"] is True, result
    assert (cfg.opt_summary or {}).get("combo_seed") == 11
