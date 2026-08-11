"""The live edge-decay rule must not halve a symbol's size off ten trades.

The rule splits a symbol's recent nets in half and compares two profit
factors; below the threshold it is comparing two 10-trade samples, which is
noise. Measured over 20000 Monte Carlo runs of a symbol whose true edge never
changes, drawn from win rates and payoffs matching this book:

    20 trades   12-17% false alarms
    30 trades    5-10%
    40 trades    4-9%
    60 trades  1.5-5%

At 20 that is about one symbol in seven cut to half size on nothing but
noise, and reopt_on_decay queues a full walk-forward behind each one. US30
was sitting at 0.5x off 21 trades while carrying the most precisely measured
holdout in the portfolio (407 trades); raising the bar to 30 returned it to
full size, while NAS100 and XAUUSD stayed throttled on the separate PF < 1.0
rule, which is evidenced by 39 and 29 trades respectively.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.supervisor import DEFAULTS, Supervisor

_pf = Supervisor._pf


def _fires(nets, threshold):
    """The rule, exactly as _review applies it."""
    if len(nets) < int(threshold):
        return False
    mid = len(nets) // 2
    older, recent = _pf(nets[:mid]), _pf(nets[mid:])
    return older > 0 and recent < older * 0.5 and recent < 1.0


def test_the_threshold_is_at_least_thirty():
    assert DEFAULTS["edge_decay_min_trades"] >= 30


@pytest.mark.parametrize("count", [10, 19, 20, 25, 29])
def test_the_rule_cannot_fire_below_the_threshold(count):
    """A sample this size cannot distinguish decay from noise."""
    # A run of losses that would trip the comparison on any long-enough sample.
    nets = [2.0] * (count // 2) + [-1.0] * (count - count // 2)
    assert not _fires(nets, DEFAULTS["edge_decay_min_trades"])


def test_a_genuine_collapse_still_trips_it_at_the_new_bar():
    """Raising the bar must not disarm the rule, only quiet it."""
    nets = [2.0] * 15 + [-1.0] * 15          # clean edge, then nothing but losses
    assert _fires(nets, DEFAULTS["edge_decay_min_trades"])


def test_a_steady_winner_is_left_alone():
    nets = ([2.0, -1.0] * 8 + [2.0, -1.0] * 8)[:32]
    assert not _fires(nets, DEFAULTS["edge_decay_min_trades"])


def test_the_false_alarm_rate_is_materially_lower_than_at_twenty():
    """The measurement the threshold was raised on, pinned as a regression."""
    rng = np.random.default_rng(42)
    runs = 4000

    def rate(count, threshold):
        hits = 0
        for _ in range(runs):
            wins = rng.random(count) < 0.45
            nets = np.where(wins, 2.2, -1.0).tolist()
            if _fires(nets, threshold):
                hits += 1
        return hits / runs

    at_20 = rate(20, 20)
    at_30 = rate(30, 30)
    assert at_20 > 0.09, f"20'de yanlis alarm beklenenden dusuk: {at_20:.3f}"
    assert at_30 < at_20 * 0.75, f"30'da anlamli dusus yok: {at_20:.3f} -> {at_30:.3f}"
