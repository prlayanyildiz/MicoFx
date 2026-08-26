"""``trail_start_atr`` is not where the trail starts protecting anything.

The level the trail places is ``close - trail_step_atr * ATR``. A stop there
only beats the original one once the gain exceeds ``trail_step_atr``, so the
point at which anything can first be locked is::

    max(trail_start_atr, trail_step_atr) / sl_atr_mult      (in R)

SpotBrent advertises ``trail_start_atr`` 0.5 and cannot protect a single tick
before 2.2 R. XAUUSD and NAS100 are the same. Six of ten symbols sit above
1.5 R while live winners average 1.08 R, which means those six have two
outcomes available to them - the full stop, or a rare run past 2.2 R - and
nothing in between.

The evidence is not only arithmetic. Across 47 ticket-matched closes on 13.08
there was exactly one trail move, and it landed on UK100, whose effective point
is 0.40 - the lowest in the book.

The simulation applies the same rule, so this is not a live/backtest split; it
is a number that reads as one thing and behaves as another, on the field an
operator looks at to answer "when does this start protecting me". Reporting it
is what stops it hiding again.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

APP_SRC = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py").read_text(
    encoding="utf-8")
ENGINE_SRC = (Path(__file__).resolve().parents[1] / "micofx" / "engine.py").read_text(
    encoding="utf-8")


def _arms_at(sl, start, step):
    """Where PROFIT can first be locked: the stop sits above entry."""
    return max(start, step) / sl if sl > 0 and (start or step) else None


def _improves_at(sl, start, step):
    """Where the stop first MOVES at all - still a losing stop, smaller loss.
    It only has to beat the original stop, which is sl below entry."""
    return max(start, step - sl) / sl if sl > 0 and (start or step) else None


# ------------------------------------------------------------- the reading

def test_the_panel_reports_both_thresholds():
    assert '"trail_arms_at_r"' in APP_SRC
    assert '"trail_improves_at_r"' in APP_SRC
    assert "max(_ts, _st) / _sl" in APP_SRC
    assert "max(_ts, _st - _sl) / _sl" in APP_SRC


def test_the_two_are_not_the_same_number():
    """Conflating them is the mistake this file exists to stop repeating:
    SpotBrent starts cutting its loss at 1.2 R and only protects profit at 2.2."""
    assert abs(_improves_at(1.0, 0.5, 2.2) - 1.2) < 1e-9
    assert abs(_arms_at(1.0, 0.5, 2.2) - 2.2) < 1e-9


def test_a_low_start_is_therefore_not_inert():
    """Measured, not argued: start 0.3 / step 2.2 produced 10 trail exits
    against 8 for start 2.2 / step 2.2 on identical bars. The low start does
    real work - it just cuts losses rather than locking gains."""
    assert _improves_at(1.0, 0.3, 2.2) < _arms_at(1.0, 0.3, 2.2)


def test_it_is_the_step_that_decides_when_the_start_is_lower():
    """SpotBrent: start 0.5, step 2.2 - nothing locks before 2.2 R."""
    assert _arms_at(1.0, 0.5, 2.2) == 2.2


def test_it_is_the_start_that_decides_when_the_step_is_lower():
    """US500: start 2.0, step 1.6."""
    assert _arms_at(1.0, 2.0, 1.6) == 2.0


def test_a_wide_stop_pulls_the_point_down_in_r():
    """GER40: start 2.0, step 2.2 on a 2.0 stop - 1.10 R, not 2.2."""
    assert abs(_arms_at(2.0, 2.0, 2.2) - 1.10) < 1e-9


def test_the_six_unreachable_symbols_are_above_the_average_winner():
    """Live winners averaged 1.08 R on 13.08."""
    for name, sl, start, step in (("JPN225", 1.0, 2.0, 2.0),
                                  ("NAS100", 1.0, 1.4, 2.2),
                                  ("US2000", 1.0, 0.8, 1.6),
                                  ("US500", 1.0, 2.0, 1.6),
                                  ("SpotBrent", 1.0, 0.5, 2.2),
                                  ("XAUUSD", 1.0, 1.0, 2.2)):
        assert _arms_at(sl, start, step) > 1.08, f"{name} ulasilabilir olmali"


def test_uk100_the_one_that_actually_trailed_is_reachable():
    assert _arms_at(1.0, 0.3, 0.4) < 1.08


# --------------------------------------------------- the rule it comes from

def test_the_engine_demands_a_minimum_improvement_not_merely_any():
    """Stronger than "must improve": the move has to clear trail_min_step,
    which is itself built from the *active* trail step (OPT step, or the
    harvest overlay once paid). That is why the step, and not the advertised
    start, decides when anything can first be locked - and it means the real
    point can sit even higher than max(start, step)."""
    assert "trail_min_step(" in ENGINE_SRC
    assert "active_step" in ENGINE_SRC
    assert "target - current_sl < step" in ENGINE_SRC


def test_the_simulation_uses_the_same_minimum():
    """models.trail_min_step says engine and backtest are its only callers,
    shared so the two cannot drift apart."""
    bt = (Path(__file__).resolve().parents[1] / "micofx" / "backtest.py").read_text(
        encoding="utf-8")
    assert "trail_min_step(" in bt


def test_the_trail_level_is_still_built_from_the_step():
    assert "trail_step_atr" in ENGINE_SRC


def test_missing_values_report_nothing_rather_than_zero():
    assert _arms_at(0.0, 1.0, 1.0) is None
    assert _arms_at(1.0, 0.0, 0.0) is None
    assert "if trail_arms else None" in APP_SRC
