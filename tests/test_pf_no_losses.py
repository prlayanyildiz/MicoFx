"""A run with no losing trades must not be judged by how many dollars it made.

``_pf`` is fed ``profit + commission + swap`` per trade - currency, not R. With
losses present it returns a dimensionless ratio; with none it used to return
the raw win SUM, so the unit of the answer changed silently while every caller
compares it against a ratio threshold of 1.0.

The consequence is backwards, and reachable at the live settings:

  * _hour_risk_scales buckets a symbol's trades by hour-of-day across the whole
    lookback window and scales that hour down when ``pf < 1.0``. Six winning
    trades in one hour totalling $0.60 returned 0.60 and earned a size cut; the
    same six winners totalling $3.60 returned 3.60 and did not. Nothing but the
    dollar size of the wins decided it, and bad_hour_min_trades is 6 live.
  * The edge-decay check fires on ``recent_pf < older_pf * 0.5 and recent_pf <
    1.0``. A recent half of fifteen trades, all winners, totalling $0.75
    returned 0.75 and tripped both halves - a perfect winning streak cut to
    half size.

A loss-free run is the best possible outcome, so it now reports a large finite
value. Finite rather than inf because this is serialised into /api/ai and
json.dumps writes ``Infinity``, which is not valid JSON.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.supervisor import DEFAULTS, PF_NO_LOSSES, Supervisor

_pf = Supervisor._pf


# ------------------------------------------------- the unit no longer changes

@pytest.mark.parametrize("nets", [
    [0.05] * 12,        # $0.60 total - used to return 0.60 and read as failing
    [0.30] * 12,        # $3.60
    [2.00] * 12,        # $24
    [0.01],             # a single tiny win
    [1e-6],
])
def test_a_run_with_no_losses_reports_the_same_thing_whatever_it_made(nets):
    assert _pf(nets) == PF_NO_LOSSES


def test_the_dollar_size_of_the_wins_no_longer_decides():
    """The whole defect in one line: these two differ only in scale."""
    assert _pf([0.05] * 12) == _pf([2.00] * 12)


def test_a_loss_free_run_clears_every_threshold_in_the_module():
    pf = _pf([0.05] * 12)
    assert pf >= DEFAULTS["quarantine_pf"]
    assert pf >= DEFAULTS["watch_pf"]
    assert pf >= DEFAULTS["bad_hour_pf"]
    assert pf >= 1.0, "kayipsiz seri hala 'kotu saat' sayiliyor"


# -------------------------------------------------- the two reachable callers

def test_an_hour_of_nothing_but_small_wins_is_not_scaled_down():
    """_hour_risk_scales: `if pf < 1.0: scales[hour] = max(0.3, pf)`."""
    assert not (_pf([0.05] * DEFAULTS["bad_hour_min_trades"]) < 1.0)


def test_an_all_winning_recent_half_does_not_trip_the_decay_check():
    """`recent_pf < older_pf * 0.5 and recent_pf < 1.0`."""
    older = [1.0] * 8 + [-0.6] * 7          # a real ratio
    recent = [0.05] * 15                    # every one a winner, small
    older_pf, recent_pf = _pf(older), _pf(recent)
    assert not (older_pf > 0 and recent_pf < older_pf * 0.5 and recent_pf < 1.0)


# ------------------------------------------------ what must keep working

def test_a_real_ratio_is_untouched():
    assert _pf([1.0] * 6 + [-1.0] * 6) == pytest.approx(1.0)
    assert _pf([2.0] * 3 + [-1.0] * 3) == pytest.approx(2.0)
    assert _pf([1.0] * 3 + [-2.0] * 3) == pytest.approx(0.5)


def test_the_ratio_is_scale_free_as_it_always_was():
    assert _pf([1.0] * 6 + [-1.0] * 6) == _pf([0.05] * 6 + [-0.05] * 6)


def test_an_all_losing_run_is_still_zero():
    assert _pf([-1.0] * 5) == 0.0
    assert _pf([-0.01]) == 0.0


def test_an_empty_run_is_still_zero():
    assert _pf([]) == 0.0
    assert _pf([0.0, 0.0]) == 0.0


# ------------------------------------------------------- it must serialise

def test_the_value_is_json_serialisable():
    """It reaches the panel through /api/ai; Infinity is not valid JSON."""
    encoded = json.dumps({"profit_factor": _pf([0.05] * 12)})
    assert "Infinity" not in encoded
    assert json.loads(encoded)["profit_factor"] == PF_NO_LOSSES


@pytest.mark.parametrize("nets", [
    [float("inf")], [float("inf"), 1.0], [float("nan")], [1.0, float("nan")],
    [1e308, 1e308], [-float("inf")],
])
def test_a_degenerate_input_never_produces_a_non_serialisable_number(nets):
    value = _pf(nets)
    encoded = json.dumps({"pf": value})
    assert "Infinity" not in encoded and "NaN" not in encoded, encoded
