"""``_plan_symbol`` must not read ``shared`` from ``_run_unsafe``'s frame.

Found by ruff F821 after BB1: the overlay call at the job-build site used a
bare ``shared`` that only exists in ``_run_unsafe``. ``POST /api/opt/run``
would NameError on the first symbol; ``_run`` catches that and files the job
as done+error, so the scan never starts. The suite missed it because nothing
called ``_plan_symbol`` with a real variants list.

The shared grid travels on the variant dict (built where ``shared`` is in
scope). This test is that path.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer

FACTORY = {
    "sl_atr_mult": [0.5, 0.7, 0.9, 1.2, 1.5, 2.0],
    "trail_start_atr": [0.3, 0.4, 0.5, 0.7, 1.0, 1.4, 2.0],
    "trail_step_atr": [0.25, 0.4, 0.6, 0.8, 1.2, 1.6, 2.2],
    "max_spread_atr": [0.05, 0.08, 0.12, 0.18],
}

OPERATOR_SL = [1.5, 2.0, 2.5, 3.0, 4.0]


class _Bars:
    def __init__(self, n: int = 800) -> None:
        self.close = np.linspace(100.0, 110.0, n)
        self.open = self.close
        self.high = self.close + 0.2
        self.low = self.close - 0.2
        self.volume = np.full(n, 100.0)
        self.spread = np.full(n, 2.0)
        self.time = (np.arange(n) * 1800 + 1_700_000_000).astype(np.int64)

    def __len__(self) -> int:
        return self.close.size


class _Client:
    def info(self, symbol):
        return {"point": 0.01, "tick_value": 1.0, "tick_size": 0.01}

    def min_stop_distance(self, symbol):
        return 0.1

    def bars(self, symbol, tf, count):
        return _Bars()


class _Store:
    def __init__(self):
        self.system = SimpleNamespace(
            trade_all_hours=False,
            day_end_flatten_min=0,
            max_cost_pct_of_risk=0.0,
            block_high_cost=False,
            charge_costs=True,
        )
        self.defaults = {"optimizer": {"grid": dict(FACTORY)}}
        self.symbols = {}

    def get_setting(self, key, default=None):
        return default


def _opt() -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = _Store()
    opt.client = _Client()
    opt._bar_snap = {}
    return opt


def test_plan_symbol_does_not_nameerror_on_shared():
    """The live scan path: first symbol, M30, operator-widened sl."""
    shared = {**FACTORY, "sl_atr_mult": list(OPERATOR_SL)}
    variants = [{
        "key": "stoch_flip",
        "strategy": "stoch_flip",
        "own": {},
        "grid": dict(shared),
        "shared": shared,
    }]
    opt = _opt()
    plan = opt._plan_symbol(
        SymbolConfig(symbol="GER40", magic=1),
        lookback_days=30, bar_cap=2000, variants=variants,
        min_trades=10, segments=3, max_combos=20, min_positive=0.5,
        plateau=0.2, timeframes=["M30"], refine_rounds=0,
    )
    assert plan["error"] == ""
    assert plan["jobs"], plan["attempts"]
    sl = plan["jobs"][0]["grid"]["sl_atr_mult"]
    assert 1.0 not in sl
    # The operator's axis must survive intact. Exact equality was too strong:
    # floor_sl_atr_search_axis re-injects the symbol's OWN live SL via
    # sl_atr_search_keep, so the incumbent stays nameable even when it sits
    # under the 0.9 floor. Deliberate and documented (JPN 04.09: the floor
    # cliffs at -33R while live 0.7->0.8 is the sweet spot; without keep the
    # WFO cannot name 0.8 at all). Here the config carries the 1.2 default.
    live_sl = SymbolConfig(symbol="GER40", magic=1).sl_atr_mult
    assert set(OPERATOR_SL) <= set(sl), f"operatorun ekseni kirpildi: {sl}"
    assert set(sl) <= set(OPERATOR_SL) | {live_sl}, (
        f"izgaraya beklenmeyen deger girdi: {sorted(set(sl) - set(OPERATOR_SL))}")
