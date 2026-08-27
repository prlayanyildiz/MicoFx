"""walk_forward and the charged holdout must score the live slot rules.

max_open comes from cfg.max_positions. block_reverse is always on in
search: live never hedges, so a sweep at max_positions=2 must not pick
parameters against a world the engine refuses. At max_positions=1 the
flag is a no-op (the slot cap already drops the opposite fill).
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest as bt
from micofx.holdout_cost import charged_holdout
from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


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


def _run(max_positions: int = 1, **kw):
    args = {
        "cfg": SymbolConfig(symbol="GER40", magic=1, max_positions=max_positions),
        "bars": _Bars(),
        "point": 0.01, "tf_seconds": 300, "grid": GRID, "min_trades": 10,
        "segments": 4, "max_combos": 8, "min_positive_ratio": 0.0,
    }
    args.update(kw)
    return bt.walk_forward(**args)


def _hold_or_base(result: dict):
    hold = ((result.get("best") or {}).get("holdout") or {})
    if hold:
        return hold
    return result.get("baseline") or {}


def test_max_positions_one_is_bit_identical_to_the_default():
    """Today's book is 1; the pass must not move a single scored trade."""
    implicit = _run(max_positions=1)
    explicit = bt.walk_forward(
        SymbolConfig(symbol="GER40", magic=1), _Bars(), 0.01, 300, GRID,
        10, 4, 8, min_positive_ratio=0.0)
    assert implicit.get("ok") == explicit.get("ok")
    a = _hold_or_base(implicit)
    b = _hold_or_base(explicit)
    assert a.get("trades") == b.get("trades")
    assert a.get("net_r") == b.get("net_r")


def test_walk_forward_ignores_leftover_max_positions(monkeypatch):
    seen: list[int] = []
    flags: list[bool] = []
    real = bt.simulate

    def wrap(*args, **kwargs):
        seen.append(int(kwargs["max_open"]))
        flags.append(bool(kwargs["block_reverse"]))
        return real(*args, **kwargs)

    monkeypatch.setattr(bt, "simulate", wrap)
    _run(max_positions=2)
    assert seen, "walk_forward never called simulate"
    assert set(seen) == {1}
    assert set(flags) == {True}


def test_max_open_from_cfg_ignores_leftover_slots():
    assert bt.max_open_from_cfg(SymbolConfig(symbol="X", magic=1)) == 1
    assert bt.max_open_from_cfg(SymbolConfig(symbol="X", magic=1, max_positions=2)) == 1
    assert bt.max_open_from_cfg(SymbolConfig(symbol="X", magic=1, max_positions=0)) == 1
    assert bt.max_open_from_cfg(object()) == 1


def test_holdout_costed_forwards_tmp_max_positions():
    apply_src = inspect.getsource(Optimizer._holdout_costed)
    slice_src = inspect.getsource(charged_holdout)
    assert "charged_holdout(" in apply_src
    assert "max_open_from_cfg" in slice_src
    assert "max_open=" in slice_src
    assert "block_reverse=True" in slice_src
