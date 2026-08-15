"""min_stop=0.0 is 'unknown', not a legal floor of zero. None is the same hole.

walk_forward used ``if min_stop else point*10``, so an explicit 0.0 (what
``min_stop_distance`` returns when symbol info is missing) became ten points
with no warning. simulate already branched on ``is None`` only, so 0.0 there
meant a zero floor. Both paths must agree.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.logbus import LOG


def test_min_stop_none_uses_ten_points():
    assert backtest.stop_floor_const(None, 0.01) == 0.1


def test_min_stop_zero_falls_back_to_ten_points_silently_here():
    """Same fallback as None, and deliberately no log line from this function.

    It runs inside the optimizer's worker processes, thousands of times per
    sweep, and logbus serialises on a thread lock that does not reach across
    processes - its rotation is a read-truncate-rewrite two processes would
    interleave. The warning is emitted once in the parent instead; see
    test_the_parent_warns_once_when_the_floor_is_unreadable below.
    """
    logs: list[tuple[str, str]] = []
    orig = LOG.emit

    def _cap(msg, level="INFO", symbol=""):
        logs.append((str(msg), str(level)))
        return orig(msg, level, symbol)

    LOG.emit = _cap
    try:
        assert backtest.stop_floor_const(0.0, 0.01) == 0.1
    finally:
        LOG.emit = orig
    assert logs == [], f"the worker must not write to the shared log: {logs}"


def test_the_parent_warns_once_when_the_floor_is_unreadable():
    """min_stop is read once per symbol in the planning step, in the parent."""
    import inspect

    from micofx.optimizer import Optimizer

    src = inspect.getsource(Optimizer)
    i = src.index("min_stop = self.client.min_stop_distance(cfg.symbol)")
    after = src[i:i + 700]
    assert "if not min_stop:" in after, "a zero floor has to be reported somewhere"
    assert "WARN" in after


def test_the_worker_side_does_not_import_the_log():
    """Import is the tell: nothing in the sweep path may reach logbus."""
    src = (Path(__file__).resolve().parents[1] / "micofx" / "backtest.py").read_text(
        encoding="utf-8")
    assert "from .logbus import" not in src


def test_min_stop_half_point_is_kept():
    assert backtest.stop_floor_const(0.5, 0.01) == 0.5
