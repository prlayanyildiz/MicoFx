"""Every ``tried`` row must carry its out-of-sample slices, not just the score.

The optimiser's per-symbol report lists every timeframe x family it swept in
``tried``. A bare in-sample ``score`` is not comparable across families and says
nothing about whether the sweep held up out of sample - which is the whole point
of the validation and holdout cuts. ``_finish_symbol`` therefore records four OOS
numbers on each tried row so the panel (and an audit) can see why a high-scoring
sweep was refused: ``val_net_r`` (validation slice), and ``hold_net_r`` /
``hold_pf`` / ``hold_n`` (the untouched holdout slice).

Fail-first guard: drop any of the four from the tried row in ``_finish_symbol``
and these assertions fail. A failed attempt (``ok`` False) has no OOS numbers to
report, so all four must stay ``None`` there rather than crash on the missing
``best``.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, symbols):
        self.symbols = {c.symbol: c for c in symbols}
        self.recorded: list[tuple] = []

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def record_opt_run(self, symbol, score, payload, applied):
        self.recorded.append((symbol, score, payload, applied))


def _opt(symbols) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._lock = threading.RLock()
    opt.store = _Store(symbols)
    opt.job = {}
    opt._cancel = threading.Event()
    opt._force_apply = False
    opt._thread = None
    # Tail is a live-incumbent readout the OOS-slice test does not exercise.
    opt._incumbent_kept_tail = lambda cfg: ""
    return opt


def _cfg(symbol="NAS100"):
    return SymbolConfig(symbol=symbol, magic=abs(hash(symbol)) % 10_000)


def _attempt(order, *, ok=True, validated=False, tf="M30", strategy="burst",
             score=39.41, val_net_r=12.3, hold=None):
    """A sweep result the way the pool hands it back to ``_finish_symbol``.

    ``hold`` None means the attempt produced no holdout slice (a real miss),
    so the row must degrade to ``None`` rather than raise.
    """
    best = None
    if ok:
        best = {"score": score, "validation": {"net_r": val_net_r}}
        if hold is not None:
            best["holdout"] = hold
    return {"timeframe": tf, "strategy": strategy, "order": order,
            "ok": ok, "validated": validated, "best": best, "error": ""}


def _tried_by_tf(opt, cfg, attempts):
    # None validated -> the "hicbir aday kapidan gecmedi" branch, which returns
    # a report carrying the tried rows without needing a live client/apply path.
    plan = {"cfg": cfg, "started": time.time(), "attempts": attempts}
    report = opt._finish_symbol(plan, apply_best=False)
    return {row["timeframe"]: row for row in report["tried"]}


def test_an_ok_attempt_records_all_four_oos_slices():
    opt = _opt([_cfg()])
    hold = {"net_r": 45.6, "profit_factor": 1.21, "trades": 525}
    rows = _tried_by_tf(opt, _cfg(), [
        _attempt(0, val_net_r=12.3, hold=hold),
    ])
    row = rows["M30"]
    assert row["val_net_r"] == 12.3
    assert row["hold_net_r"] == 45.6
    assert row["hold_pf"] == 1.21
    assert row["hold_n"] == 525


def test_a_failed_attempt_leaves_every_oos_slice_none():
    opt = _opt([_cfg()])
    rows = _tried_by_tf(opt, _cfg(), [
        _attempt(0, ok=False, tf="M15"),
    ])
    row = rows["M15"]
    for key in ("val_net_r", "hold_net_r", "hold_pf", "hold_n"):
        assert row[key] is None, key


def test_a_missing_holdout_slice_is_none_not_a_crash():
    opt = _opt([_cfg()])
    rows = _tried_by_tf(opt, _cfg(), [
        _attempt(0, val_net_r=8.0, hold=None),
    ])
    row = rows["M30"]
    assert row["val_net_r"] == 8.0
    assert row["hold_net_r"] is None
    assert row["hold_pf"] is None
    assert row["hold_n"] is None
