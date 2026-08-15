"""An unreadable point must stop the search, not be replaced with a guess.

walk_forward substituted 1e-5 for any non-positive ``point``. That is not a
conservative default - it is a made-up price scale, and every cost in the
sweep is measured against it:

    spread_price = bars.spread * point
    cost_price   = spread_price + commission_price

On an index quoting point 0.01 the substitution understates spread by a
factor of a thousand, so the search prices trading as very nearly free and
the cost gates it feeds (max_cost_share, MAX_COST_PER_TRADE_R) wave
everything through.

The consequence is not a slightly optimistic number. On the same 3000 bars
with a 30-point spread:

    point 0.01 (real)   ok=False, no viable config at all
    point 0   (guessed) ok=True,  a winner with cost_per_trade_r 0.0003

"nothing here is tradable" becomes "here is your config, and it costs
nothing" - the exact shape of a backtest that looks excellent and loses live.

Optimizer._plan_symbol guards ``info is None`` but never the point inside it,
so a partially populated symbol_info reaches this unguarded. Refusing matches
what the rest of the codebase already does with an unusable cost input:
cost_by_hour raises 503 on the same condition, and IndicatorCache treats a
missing cost series as "produce no signals" rather than invent one.

Not proven: that this broker ever reports point 0. What is proven is that
nothing between symbol_info and the cost model checks, and what happens when
it is not checked.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest as bt
from micofx.models import SymbolConfig


class _Bars:
    def __init__(self, n: int = 3000, spread: float = 30.0) -> None:
        rng = np.random.default_rng(11)
        step = rng.normal(0.0, 0.35, n) + 0.02 * np.sin(np.arange(n) / 40.0)
        close = (100 + np.cumsum(step)).astype(np.float64)
        self.close = close
        self.open = close
        self.high = close + np.abs(rng.normal(0.25, 0.1, n))
        self.low = close - np.abs(rng.normal(0.25, 0.1, n))
        self.volume = np.full(n, 100.0)
        self.spread = np.full(n, spread)
        self.time = (np.arange(n) * 300 + 1_700_000_000).astype(np.int64)

    def __len__(self) -> int:
        return self.close.size


GRID = {"t3_length": [5, 8], "sl_atr_mult": [1.5, 2.0]}


def _run(point, **kw):
    args = {"cfg": SymbolConfig(symbol="GER40", magic=1), "bars": _Bars(),
                "point": point, "tf_seconds": 300, "grid": GRID, "min_trades": 10,
                "segments": 4, "max_combos": 8}
    args.update(kw)
    return bt.walk_forward(**args)


@pytest.mark.parametrize("point", [0.0, -1.0, -1e-9, -1e9])
def test_a_non_positive_point_refuses_the_search(point):
    result = _run(point)
    assert result["ok"] is False
    assert "point" in result["error"].lower()
    # It must not report a winner of any kind.
    assert not result.get("best")
    assert not result.get("top")


@pytest.mark.parametrize("point", [0.0, -1.0])
def test_it_never_reports_a_config_that_costs_nothing(point):
    """The specific harm: a fabricated scale prices trading as free."""
    result = _run(point)
    holdout = (result.get("best") or {}).get("holdout") or {}
    assert not holdout, "gecersiz point ile holdout uretildi"


def test_a_real_point_is_untouched():
    """The guard must not disturb a normal run."""
    result = _run(1e-5)
    assert "point degeri okunamadi" not in (result.get("error") or "")


def test_the_error_names_the_symbol():
    """It arrives in a per-symbol attempt list; an unnamed error is useless."""
    assert "GER40" in _run(0.0)["error"]


def test_nan_is_refused_too():
    """NaN > 0 is False, so it takes the same branch - assert it stays that way."""
    result = _run(float("nan"))
    assert result["ok"] is False
    assert "point" in result["error"].lower()


def test_the_substitution_is_gone_from_the_source():
    """Guards the fix: reintroducing a default silently restores the bug."""
    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "backtest.py").read_text(encoding="utf-8")
    body = src.split("def walk_forward(", 1)[1].split("\ndef ", 1)[0]
    assert "else 1e-5" not in body, "point icin uydurma varsayilan geri gelmis"
