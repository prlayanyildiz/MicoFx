"""The search must not admit a config the live cost gate will refuse.

Two gates measure the same quantity - cost as a fraction of the trade's own
risk - against two different numbers:

  * ``Optimizer.MAX_COST_PER_TRADE_R = 0.25``, applied to the holdout's
    ``cost_per_trade_r`` when deciding whether to accept a candidate.
  * ``system.max_cost_pct_of_risk``, applied per entry by ``_try_entry`` using
    the live tick spread, and refusing the trade outright when exceeded.

They ship in agreement: ``SystemConfig.max_cost_pct_of_risk`` defaults to 25.0.
They diverge the moment an operator tightens the live one, and nothing notices.
Live right now it is **18.0**, and USDJPY carries a config whose own holdout
cost is **0.1867** - comfortably inside the search's 0.25, and above the 0.18
the engine enforces. Four of its six signals are refused with ``maliyet``. The
search validated, applied and stamped a configuration that cannot trade at its
own average cost.

The fix is the one already applied to ``min_positive_ratio`` a line above, whose
comment names this exact failure: "a hardcoded 0.6 here silently overrode any
lower value the user configured: the search would admit/validate a 0.4-0.59
candidate exactly as asked, then this gate re-rejected it anyway with a
threshold the user never set".

Tighter only. A live gate looser than 0.25 does not raise the search's ceiling -
that constant carries its own reasoning and relaxing it is not this fix's job -
and a disabled live gate (``block_high_cost`` off) refuses nothing, so there is
nothing to align with.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


class _System:
    def __init__(self, pct: float = 25.0, block: bool = True):
        self.max_cost_pct_of_risk = pct
        self.block_high_cost = block


class _Store:
    def __init__(self, system):
        self.system = system

    def opt_params(self):
        return {}


def _opt(pct: float = 25.0, block: bool = True) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = _Store(_System(pct, block))
    return opt


def _best(cost_r: float) -> dict:
    """A candidate that passes every other bar in reject_reason()."""
    return {
        "score": 12.0,
        "positive_ratio": 1.0,
        "holdout": {"trades": 200, "expectancy": 0.30, "net_r": 60.0,
                    "cost_per_trade_r": cost_r, "profit_factor": 1.4},
        "validation": {"trades": 100, "net_r": 30.0, "profit_factor": 1.3},
        "selection": {"trades": 300, "net_r": 90.0, "profit_factor": 1.4},
    }


def _reason(pct: float, cost_r: float, block: bool = True) -> str:
    return _opt(pct, block).reject_reason(None, _best(cost_r))


# --------------------------------------------------- the live gate is respected

def test_a_candidate_the_engine_would_refuse_is_not_accepted():
    """USDJPY's case: 0.1867 holdout cost against a live gate of 18%."""
    assert "maliyet" in _reason(18.0, 0.1867), (
        "canli kapinin reddedecegi konfig aramadan gecti")


@pytest.mark.parametrize("cost_r", [0.19, 0.20, 0.24])
def test_everything_between_the_two_thresholds_is_refused(cost_r):
    assert _reason(18.0, cost_r) != ""


def test_a_candidate_inside_the_live_gate_still_passes():
    assert _reason(18.0, 0.10) == ""


def test_the_boundary_itself_is_allowed():
    assert _reason(18.0, 0.18) == ""
    assert _reason(18.0, 0.1801) != ""


# ------------------------------------------------- tighter only, never looser

def test_a_looser_live_gate_does_not_raise_the_shipped_ceiling():
    """The 0.25 constant carries its own reasoning; this must not relax it."""
    assert _reason(40.0, 0.30) != "", "canli kapi gevsek diye tavan yukselmis"
    assert _reason(40.0, 0.20) == ""


def test_the_shipped_default_behaves_exactly_as_before():
    assert _reason(25.0, 0.24) == ""
    assert _reason(25.0, 0.26) != ""


def test_a_disabled_live_gate_leaves_the_search_alone():
    """block_high_cost off means the engine refuses nothing on cost."""
    assert _reason(18.0, 0.20, block=False) == ""
    assert _reason(18.0, 0.26, block=False) != ""


# ------------------------------------------------------------ degenerate input

def test_a_zero_or_negative_live_setting_is_ignored():
    """0 disables the live gate the same way block_high_cost off does."""
    assert _reason(0.0, 0.20) == ""
    assert _reason(-5.0, 0.20) == ""


def test_a_missing_system_does_not_break_the_gate():
    opt = Optimizer.__new__(Optimizer)
    opt.store = None
    assert opt.reject_reason(None, _best(0.20)) == ""
    assert opt.reject_reason(None, _best(0.30)) != ""
