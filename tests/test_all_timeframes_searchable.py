"""Every family may be searched on every configured timeframe.

The family->timeframe map used to keep the scalps on M5 and hand M15+ to the
swing families, on a budget argument its own comment stated: "so the opt budget
is not wasted pairing micro_rev with H1". That argument does not survive
contact with how the budget actually works - ``max_combos`` is spent per sweep
(one family x one timeframe), not shared across the search, so an extra pairing
costs wall-clock and takes nothing away from the pairings already running.

What the restriction did cost was optionality. M5 has been applied 55 times in
this system's history, and the pairings that won were not the ones anyone would
have predicted: XAUUSD came back with micro_rev/M5 and NAS100 with
stoch_flip/M5. Deciding in advance which family suits which bar length is the
kind of judgement the out-of-sample gates exist to make on evidence.

Opening the timeframes alone would have been a half-change. ``uses_swing_exits``
refused the wider exit grid to any scalp family whatever the bar length, so
micro_rev on H1 would have been searched with a stop envelope sized for
five-minute bars - the exact failure SWING_GRID_OVERLAY's own comment describes:
"the search only ever offers H1 candidates a stop tight enough to be noise". The
envelope now follows the bar, which is what its docstring said all along:
"Longer bars (or non-scalp families) need the wider exit search envelope."
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import (
    SCALP_STRATEGIES,
    STRATEGIES,
    STRATEGY_TIMEFRAMES,
    TIMEFRAMES,
    is_scalp_strategy,
    strategy_allows_timeframe,
    uses_swing_exits,
)

# ------------------------------------------------- every pairing is searchable

@pytest.mark.parametrize("strategy", sorted(STRATEGIES))
@pytest.mark.parametrize("timeframe", TIMEFRAMES)
def test_every_family_may_search_every_timeframe(strategy, timeframe):
    assert strategy_allows_timeframe(strategy, timeframe), (
        f"{strategy}/{timeframe} aramaya giremiyor")


def test_the_scalp_families_reach_the_longest_offered_bar_too():
    """No family is fenced off a timeframe; the search decides on the numbers.

    Written against H1 three times as that bar came and went. The rule under it
    never moved and is what this now asserts directly: whatever the longest
    offered bar happens to be, a scalp family may be paired with it and the
    holdout picks. Fencing by family name was always a guess about where a
    strategy works, made before the measurement instead of after it.
    """
    longest = TIMEFRAMES[-1]
    for family in sorted(SCALP_STRATEGIES):
        assert strategy_allows_timeframe(family, longest)


def test_the_swing_families_reach_the_five_minute_chart():
    # Drawn from STRATEGIES rather than hardcoded: this list still named
    # trix_flip after it was retired on 14.08, and strategy_allows_timeframe
    # answers True for any name it does not know - so the assertion passed
    # while testing a family that no longer exists. A test that cannot fail
    # is worse than no test. Cursor's scan #080 found it.
    swing = [f for f in STRATEGIES if f not in SCALP_STRATEGIES]
    assert swing, "no swing family left to test"
    for family in swing:
        assert strategy_allows_timeframe(family, "M5")


def test_a_retired_family_is_not_quietly_accepted():
    """The reason the leftover above went unnoticed for a whole release."""
    from micofx.strategy import _FAMILIES

    for retired in ("trix_flip", "flow_rev"):
        assert retired not in _FAMILIES
        assert retired not in STRATEGIES


# ------------------------------------------- the exit envelope follows the bar

@pytest.mark.parametrize("strategy", sorted(STRATEGIES))
def test_the_wider_exit_grid_is_decided_by_bar_length_not_by_family(strategy):
    assert uses_swing_exits(strategy, "M5") is False
    for tf in ("M15", "M30"):
        assert uses_swing_exits(strategy, tf) is True, (
            f"{strategy}/{tf} hala scalp olcusunde stop izgarasiyla araniyor")


def test_a_scalp_family_on_long_bars_gets_the_swing_envelope():
    """micro_rev/M30 used to search with a five-minute stop grid.

    Written for micro_rev/H1; the hazard is the same at any bar longer than the
    family's name suggests, and M30 is the longest one offered now.
    """
    assert is_scalp_strategy("micro_rev")
    assert uses_swing_exits("micro_rev", "M30") is True
    assert uses_swing_exits("micro_rev", "M5") is False


def test_scalp_classification_itself_is_unchanged():
    """Position caps and cooldowns read this; only the exit grid moved."""
    assert SCALP_STRATEGIES == frozenset({"micro_rev", "burst"})


# ---------------------------------------------------- no timeframe crumbs left

def test_no_family_is_restricted_any_more():
    assert STRATEGY_TIMEFRAMES == {}, (
        "aile bazli TF kisiti geri gelmis")


def test_an_explicit_restriction_still_works_if_one_is_ever_added():
    """The mechanism stays; only the shipped restrictions are gone."""
    allow = {"micro_rev": ["M5"]}
    assert strategy_allows_timeframe("micro_rev", "M5", allow)
    assert not strategy_allows_timeframe("micro_rev", "H1", allow)


def test_an_empty_list_still_means_nothing_rather_than_everything():
    allow = {"micro_rev": []}
    for tf in TIMEFRAMES:
        assert not strategy_allows_timeframe("micro_rev", tf, allow)


def test_an_unrecognised_bar_never_claims_the_swing_envelope():
    """Retired names are handled in test_no_retired_timeframes.py; here it is
    enough that anything unknown falls to the narrow envelope rather than the
    wide one."""
    assert uses_swing_exits("t3_stoch", "beklenmeyen") is False
    assert uses_swing_exits("t3_stoch", "") is False


def test_the_searchable_timeframes_are_exactly_these_three():
    """Each name here left on a measurement, not on an argument.

    M1: 0.099 R/trade against M5's 0.121, at 0.043 R/trade of cost against
    0.024, on a quarter of the history. M3 the same way.

    H1 is the one that moved twice. It left 14.08 on a wall-clock guess, which
    was not a measurement and should not have counted; came back 15.08 on a
    real cost reading (UK100 spends 21.3% of R on spread at M5 against 8.6% at
    H1); and left again that evening on a yield reading that outranks it -
    0.110 R/**day** against M5's 1.303. Per trade the hourly bar is cheaper and
    per day it is far poorer, and at this account size the day is what compounds.
    The cost problem was answered by moving the expensive symbols instead.

    Reopening it needs a R/day number, not a spread number.
    """
    assert TIMEFRAMES == ["M5", "M15", "M30"]
