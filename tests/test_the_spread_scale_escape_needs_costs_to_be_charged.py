"""With costs off, the spread-scale escape drops the incumbent guard for nothing.

``_beats_incumbent`` normally refuses a candidate whose holdout scores below the
live config's. It waives that comparison when the spread assumption has moved -
when the scale stamped on the incumbent differs from today's measured one by
more than half a ratio bucket - and the reasoning is sound while costs are
charged:

    the search starts charging a different - higher - cost than the incumbent
    was ever scored against ... The older number is not better, it is
    differently measured.

``charge_costs=False`` (DECISIONS 21) zeroes the spread series before anything
is scored, so the scale multiplies nothing and both numbers are measured on
identical terms. The premise is simply false, and the escape then drops the one
guard standing between a weaker candidate and a live symbol.

It is not theoretical. XAUUSD carries a stamp of 1.25 against a measured 1.15,
and the log records the escape firing at 13:20 today - after costs went off at
about 11:20:

    XAUUSD: mevcut ayar farkli spread olcegiyle olculmus (1.25 -> 1.15),
    skor kiyasi atlandi - aday kendi kapilariyla degerlendirildi.

That candidate was refused further down for an unrelated reason, so nothing has
been mis-applied yet. The guard was still dropped on a premise that no longer
holds.

Only the escape is conditioned. Everything else in the method is untouched, and
with costs charged the behaviour is exactly what it was.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer

OPTIMIZER_SRC = (Path(__file__).resolve().parents[1]
                 / "micofx" / "optimizer.py").read_text(encoding="utf-8")


class _System:
    def __init__(self, charge):
        self.charge_costs = charge
        self.block_high_cost = False
        self.max_cost_pct_of_risk = 25.0


class _Store:
    def __init__(self, charge):
        self.system = _System(charge)


class _Cfg:
    symbol = "XAUUSD"
    opt_summary = {"spread_scale": 1.25, "holdout": {"score": 40.0}}
    # Inside INCUMBENT_GUARD_DAYS, or the age check returns True before the
    # escape is ever reached and the test would pass on the wrong branch.
    opt_updated_at = time.time()


def _optimizer(charge: bool, measured: float):
    opt = object.__new__(Optimizer)
    opt.store = _Store(charge)
    opt._spread_scale = lambda symbol: measured        # type: ignore[assignment]
    return opt


# ------------------------------------------------------------- the defect

def test_with_costs_off_a_weaker_candidate_is_still_refused():
    """Stamp 1.25 against a measured 1.15 - the escape's own trigger."""
    opt = _optimizer(charge=False, measured=1.15)
    assert opt._beats_incumbent(_Cfg(), {"score": 5.0}) is False, (
        "maliyet kapaliyken spread olcegi hicbir skoru etkilemiyor - "
        "mevcut ayarin korumasi bosuna dusuruldu")


def test_with_costs_charged_the_escape_still_works():
    """The original behaviour, unchanged: the two scores are not comparable."""
    opt = _optimizer(charge=True, measured=1.15)
    assert opt._beats_incumbent(_Cfg(), {"score": 5.0}) is True


# --------------------------------------------------- what must keep working

def test_a_stronger_candidate_still_wins_either_way():
    for charge in (True, False):
        opt = _optimizer(charge=charge, measured=1.15)
        assert opt._beats_incumbent(_Cfg(), {"score": 99.0}) is True


def test_a_scale_that_has_not_moved_compares_scores_either_way():
    for charge in (True, False):
        opt = _optimizer(charge=charge, measured=1.25)
        assert opt._beats_incumbent(_Cfg(), {"score": 5.0}) is False
        assert opt._beats_incumbent(_Cfg(), {"score": 99.0}) is True


def test_a_missing_system_defaults_to_charging():
    """Same direction as everywhere else: absent information keeps the older,
    stricter reading rather than inventing a licence."""
    opt = object.__new__(Optimizer)
    opt.store = None
    opt._spread_scale = lambda symbol: 1.15           # type: ignore[assignment]
    assert opt._beats_incumbent(_Cfg(), {"score": 5.0}) is True


def test_the_escape_still_explains_itself_in_the_log():
    assert "skor kiyasi " in OPTIMIZER_SRC and "atlandi - aday" in OPTIMIZER_SRC
