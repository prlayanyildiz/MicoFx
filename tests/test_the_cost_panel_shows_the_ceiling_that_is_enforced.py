"""The panel judged cost against 0.25 while the engine refuses entries at 0.18.

``portfolio-gates`` took its ceiling straight from
``Optimizer.MAX_COST_PER_TRADE_R`` - the constant, 0.25 - and used it twice: it
is reported as ``cost_ceiling_r``, and it decides the ``maliyet`` flag.

The engine does not use that number. ``_try_entry`` refuses an entry when the
trade's live cost exceeds ``system.max_cost_pct_of_risk``, which ships at 25.0
so the two agree out of the box and sits at **18.0** on this account. The
optimiser already knows this and aligns against it - ``reject_reason`` takes
``min(MAX_COST_PER_TRADE_R, live_pct / 100)`` and its comment spells out why:
"the two only diverge once an operator tightens the live one, and nothing
noticed when they did."

The panel was the copy that still had not noticed. A config whose cost sits
between 0.18 and 0.25 reads as passing on the screen while every one of its
entries is refused at the broker - which is precisely the state the panel
exists to make visible. Nothing in the book is in that band today (FRA40 is
highest at 0.105), so no row is currently mislabelled; the reported ceiling,
however, has been wrong on all ten rows.

Tighter only, exactly as the optimiser does it. A live gate above 0.25 does not
raise the panel's ceiling - the constant carries its own reasoning - and a
disabled or zeroed live gate refuses nothing, so there is nothing to align
with and the constant stands.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.web.app import _enforced_cost_ceiling


class _System:
    def __init__(self, block, pct):
        self.block_high_cost = block
        self.max_cost_pct_of_risk = pct


class _Store:
    def __init__(self, system):
        self.system = system


class _Opt:
    MAX_COST_PER_TRADE_R = 0.25


# ------------------------------------------------------------- the defect

def test_a_tightened_live_gate_lowers_the_panel_ceiling():
    assert _enforced_cost_ceiling(_Opt(), _Store(_System(True, 18.0))) == 0.18


def test_the_flag_follows_the_gate_that_actually_refuses():
    """A config at 0.20 passes the constant and fails the broker."""
    ceiling = _enforced_cost_ceiling(_Opt(), _Store(_System(True, 18.0)))
    assert 0.20 > ceiling, "panel 0.20'yi gecer sayardi, motor reddediyor"


# --------------------------------------------------- what must keep working

def test_a_looser_live_gate_does_not_raise_the_ceiling():
    """Tighter only - the constant carries its own reasoning."""
    assert _enforced_cost_ceiling(_Opt(), _Store(_System(True, 90.0))) == 0.25


def test_a_disabled_gate_leaves_the_constant_alone():
    assert _enforced_cost_ceiling(_Opt(), _Store(_System(False, 18.0))) == 0.25


def test_a_zeroed_gate_refuses_nothing_so_there_is_nothing_to_align_with():
    assert _enforced_cost_ceiling(_Opt(), _Store(_System(True, 0.0))) == 0.25


def test_a_missing_system_or_optimiser_falls_back_to_the_constant():
    assert _enforced_cost_ceiling(_Opt(), None) == 0.25
    assert _enforced_cost_ceiling(None, _Store(_System(True, 18.0))) == 0.18


def test_it_matches_what_the_optimiser_computes_for_the_same_inputs():
    """Two copies of one policy; if they drift again this is where it shows."""
    from micofx.optimizer import Optimizer
    for pct in (5.0, 18.0, 25.0, 40.0):
        mine = _enforced_cost_ceiling(_Opt(), _Store(_System(True, pct)))
        theirs = min(Optimizer.MAX_COST_PER_TRADE_R, pct / 100.0)
        assert mine == theirs, f"%{pct} icin panel {mine}, optimizer {theirs}"
