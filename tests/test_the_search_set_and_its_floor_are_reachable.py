"""Two settings nothing could change were the reason no search applied.

Found 11.09 while chasing the operator's "taramada isle yaramiyor aile vs
bulamiyr":

- ``strategies`` held 5 families in the store while defaults.json shipped 7.
  ``range_fade`` - NAS100's best candidate of the whole evening, +21.5R
  holdout at PF 1.45 - was not in the live search set at all. The family
  could not be found because it was never looked for.
- ``min_positive_ratio`` held 0.7, which is not a value the ratio can take.
  It is ``wins / HOLDOUT_ROBUST_PARTS`` over 6 equal holdout sub-windows, so
  the rungs are 0, 1/6, 2/6 ... 1. A 0.7 floor silently means **5/6 (83%)**.
  US30's validated keltner_break candidate (+26.2R, PF 1.15) died at 4/6.

Neither was reachable. Both are outside ``_OPERATOR_OPT_FIELDS``, so the
panel answered 400; ``Store.opt_params`` merges ``{**shipped, **stored}``, so
editing defaults.json does not reach a live book either - the same trap the
grid-axes note in app.py records. The only remaining door was a direct write
to a database the live process owns exclusively.

So the door is open now, and bounded: the operator gets the dial, a session
cookie still cannot switch the gate off or invent a family.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.models import STRATEGIES
from micofx.web.app import (
    _OPERATOR_OPT_FIELDS,
    _OPT_PARAM_BOUNDS,
    _positive_ratio_note,
)

# ------------------------------------------------------------- the door

def test_both_settings_are_writable():
    assert "strategies" in _OPERATOR_OPT_FIELDS
    assert "min_positive_ratio" in _OPERATOR_OPT_FIELDS


def test_the_floor_is_still_a_floor():
    """Writable is not the same as removable."""
    low, high, _ = _OPT_PARAM_BOUNDS["min_positive_ratio"]
    assert low > 0.0, "0 would switch F6 off entirely"
    assert low <= 0.6, "the shipped default must remain settable"
    assert high == 1.0


def test_the_rest_of_the_blob_stays_hands_off():
    """Opening two names must not open the search's guts."""
    for name in ("min_trades", "segments", "strategy_grids", "holdout_days",
                 "plateau_weight", "coverage_budget", "strategy_max_combos"):
        assert name not in _OPERATOR_OPT_FIELDS, name


# ------------------------------------------- the ratio says what it means

def test_a_value_on_the_lattice_says_nothing():
    for rung in (0.0, 1 / 6, 2 / 6, 0.5, 4 / 6, 5 / 6, 1.0):
        assert _positive_ratio_note(rung) == "", rung


def test_the_value_that_froze_the_book_is_called_out():
    note = _positive_ratio_note(0.7)
    assert note, "0.7 must not pass silently"
    assert "5/6" in note, note
    assert "83" in note, note


def test_an_in_between_value_names_the_rung_it_becomes():
    assert "1/6" in _positive_ratio_note(0.1)
    assert "3/6" in _positive_ratio_note(0.45)
    assert "6/6" in _positive_ratio_note(0.9)


def test_the_note_is_derived_from_the_constant_not_a_hardcoded_six():
    """If HOLDOUT_ROBUST_PARTS ever moves, the advice must move with it."""
    assert backtest.HOLDOUT_ROBUST_PARTS == 6
    note = _positive_ratio_note(0.7)
    assert f"/{backtest.HOLDOUT_ROBUST_PARTS}" in note


# ---------------------------------------------- the shipped set is the set

def test_the_shipped_families_are_the_living_families():
    """defaults.json and STRATEGIES must not drift again."""
    import json

    root = Path(__file__).resolve().parents[1]
    cfg = json.loads((root / "config" / "defaults.json").read_text("utf-8-sig"))
    shipped = set(cfg["optimizer"]["strategies"])
    assert shipped == set(STRATEGIES), (
        f"fazla={sorted(shipped - set(STRATEGIES))} "
        f"eksik={sorted(set(STRATEGIES) - shipped)}")
