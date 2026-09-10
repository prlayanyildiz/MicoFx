"""The shakeout floor reads the tail, and reads only the tail.

``shakeout_sl_atr_mult`` is called once per entry by both live and
``backtest.simulate``. In the backtest the autopsy list it scans grows with
every trade the run books, and the function used to walk the whole list and
then slice ``[-WINDOW:]`` - the same answer for O(all closes) work. A profile
of one GER40 walk_forward put it at 717,002 calls and 175s of 491s: 36% of a
search spent recomputing the same ten rows.

It walks backwards and stops at the window now. That is a speed change and
must not be a behaviour change, so this file pins the equivalence rather than
the implementation: the answer for a long list must equal the answer for its
tail alone.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.risk import _SHAKEOUT_SL_WINDOW, shakeout_sl_atr_mult

SYM = "_bt"


def _row(reason: str, r: float, t: float = 100.0, sym: str = SYM) -> dict:
    return {"symbol": sym, "exit_reason": reason, "r_realised": r,
            "exit_time": t, "mfe_r": 0.5, "mae_r": 0.9, "risk_dist": 1.0}


def test_only_the_last_window_matters():
    """Rows older than the window cannot change the answer - that is what
    makes stopping early safe."""
    tail = [_row("sl", -1.0) for _ in range(_SHAKEOUT_SL_WINDOW)]
    noise = [_row("trail", 0.9) for _ in range(400)]
    assert shakeout_sl_atr_mult(1.0, SYM, noise + tail) == \
        shakeout_sl_atr_mult(1.0, SYM, tail)


def test_a_long_history_equals_its_own_tail(): 
    """Randomised: for any history, the answer equals the answer for the last
    WINDOW matching rows on their own."""
    random.seed(11)
    for _ in range(500):
        rows = [_row(random.choice(["sl", "trail", "flatten"]),
                     random.choice([-1.0, -0.3, 0.8]),
                     sym=random.choice([SYM, "OTHER"]))
                for _ in range(random.randint(0, 60))]
        mine = [r for r in rows if r["symbol"] == SYM]
        for base in (0.5, 1.0, 1.2, 2.5):
            assert shakeout_sl_atr_mult(base, SYM, rows) == \
                shakeout_sl_atr_mult(base, SYM, mine[-_SHAKEOUT_SL_WINDOW:]), rows


def test_the_symbol_filter_still_applies():
    """Another symbol's deaths must not floor this symbol's stop, and they sit
    in the same list live."""
    others = [_row("sl", -1.0, sym="OTHER") for _ in range(50)]
    assert shakeout_sl_atr_mult(1.0, SYM, others) == 1.0


def test_the_since_filter_still_applies():
    """A fresh apply does not inherit the previous config's SL streak (F7)."""
    old = [_row("sl", -1.0, t=100.0) for _ in range(_SHAKEOUT_SL_WINDOW)]
    assert shakeout_sl_atr_mult(1.0, SYM, old, 0.0) > 1.0      # legacy: counts
    assert shakeout_sl_atr_mult(1.0, SYM, old, 500.0) == 1.0   # all pre-date it


def test_a_none_row_does_not_break_the_scan():
    rows = [None, *[_row("sl", -1.0) for _ in range(_SHAKEOUT_SL_WINDOW)], None]
    assert shakeout_sl_atr_mult(1.0, SYM, rows) > 1.0
