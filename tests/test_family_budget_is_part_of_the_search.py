"""BUDGET-1: per-family search budget, falling back to the global max_combos.

A single global 2000 puts every live family in a draw. GER40's stoch_flip
grid is 28800 and finishes in 24 minutes; a family without an override
keeps the global cap. The override has to travel on the job dict (the
worker is a spawned process) and the stamp already records max_combos from
that job.

Default: omitted map, missing family, or an unreadable value keep the
global budget so live searches do not move until Claude writes the map.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_closed_symbol_scan_does_not_apply import _finish_opt, _finish_plan
from test_plan_symbol_reads_shared_from_variant import (
    FACTORY,
    Optimizer,
    SymbolConfig,
    _Client,
)

from micofx.models import STRATEGIES
from micofx.optimizer import family_max_combos, run_combo_budget


def _store_with(blob: dict):
    class Store:
        def __init__(self):
            self.defaults = {"optimizer": {"grid": dict(FACTORY)}}
            self.symbols = {}
            self._blob = blob
            self.system = SimpleNamespace(
                trade_all_hours=False,
                day_end_flatten_min=0,
                max_cost_pct_of_risk=0.0,
                block_high_cost=False,
                charge_costs=True,
            )

        def get_setting(self, key, default=None):
            return default

        def opt_params(self):
            return dict(self._blob)

    return Store()


def _opt(blob: dict) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = _store_with(blob)
    opt.client = _Client()
    opt._bar_snap = {}
    return opt


def _variants(*families: str) -> list[dict]:
    shared = dict(FACTORY)
    return [{
        "key": fam, "strategy": fam, "own": {},
        "grid": dict(shared), "shared": shared,
    } for fam in families]


def _plan(opt: Optimizer, families: tuple[str, ...], max_combos: int = 2000):
    return opt._plan_symbol(
        SymbolConfig(symbol="GER40", magic=1),
        lookback_days=30, bar_cap=2000, variants=_variants(*families),
        min_trades=10, segments=3, max_combos=max_combos, min_positive=0.5,
        plateau=0.2, timeframes=["M30"], refine_rounds=0,
    )


def test_family_max_combos_falls_back_when_the_map_is_absent():
    assert family_max_combos({}, "stoch_flip", 2000) == 2000
    assert family_max_combos(None, "stoch_flip", 2000) == 2000
    assert family_max_combos({"strategy_max_combos": {}}, "stoch_flip", 2000) == 2000


def test_family_max_combos_reads_only_that_family():
    blob = {"strategy_max_combos": {"stoch_flip": 28800}}
    assert family_max_combos(blob, "stoch_flip", 2000) == 28800
    assert family_max_combos(blob, "burst", 2000) == 2000


def test_family_max_combos_rejects_unreadable_and_non_positive():
    blob = {"strategy_max_combos": {
        "stoch_flip": "nope", "burst": 0, "mtf_pullback": -1,
    }}
    assert family_max_combos(blob, "stoch_flip", 2000) == 2000
    assert family_max_combos(blob, "burst", 2000) == 2000
    assert family_max_combos(blob, "mtf_pullback", 2000) == 2000


def test_plan_puts_the_family_budget_on_the_job_dict():
    """Worker reads payload['max_combos']; a parent-only override would die."""
    opt = _opt({"strategy_max_combos": {"stoch_flip": 28800}})
    plan = _plan(opt, ("stoch_flip", "burst"))
    assert plan["error"] == ""
    by_fam = {j["strategy"]: j["max_combos"] for j in plan["jobs"]}
    assert by_fam["stoch_flip"] == 28800
    assert by_fam["burst"] == 2000


def test_combo_total_uses_the_family_cap_not_the_global_one():
    """Live tonight: stoch_flip 28800, everyone else 2000, refine_rounds=5."""
    families = list(STRATEGIES)
    blob = {"strategy_max_combos": {"stoch_flip": 28800}}
    total, per_sweep = run_combo_budget(
        blob, families, ["M5", "M15", "M30"], 2000, 5, n_symbols=6)
    assert per_sweep["stoch_flip"] == 28800 * 6
    n_other = len(families) - 1
    assert per_sweep["burst"] == 2000 * 6
    assert total == 6 * 3 * (n_other * 12000 + 172800)


def test_combo_total_without_a_family_map_matches_the_old_global_product():
    families = ["burst", "stoch_flip"]
    total, per_sweep = run_combo_budget(
        {}, families, ["M5", "M30"], 2000, 5, n_symbols=3)
    assert per_sweep["burst"] == per_sweep["stoch_flip"] == 12000
    assert total == 3 * 2 * 2 * 12000


def test_plan_without_a_family_map_keeps_the_global_budget():
    opt = _opt({})
    plan = _plan(opt, ("stoch_flip", "burst"), max_combos=2000)
    assert plan["jobs"]
    assert {j["max_combos"] for j in plan["jobs"]} == {2000}


def test_opt_run_payload_carries_the_ranked_finalists():
    opt, store = _finish_opt()
    plan, _ = _finish_plan(enabled=False)
    plan["attempts"][0]["top"] = [
        {
            "params": {"sl_atr_mult": 1.0, "trail_step_atr": 2.2},
            "score": 12.0,
            "validation": {"net_r": 10.0, "profit_factor": 1.2, "expectancy": 0.1},
            "holdout": {"net_r": 8.0, "profit_factor": 1.1, "expectancy": 0.08},
        },
        {
            "params": {"sl_atr_mult": 0.7},
            "score": 11.0,
            "validation": {"net_r": 9.0},
            "holdout": {"net_r": 20.0},
        },
    ]
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    opt._finish_symbol(plan, apply_best=False)
    payload = store.runs[-1]["payload"]
    top = payload["top"]
    assert len(top) == 2
    assert top[0]["params"]["sl_atr_mult"] == 1.0
    assert top[0]["validation"]["net_r"] == 10.0
    assert top[0]["holdout"]["net_r"] == 8.0
    assert top[1]["holdout"]["net_r"] == 20.0
