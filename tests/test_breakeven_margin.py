"""How far a config sits above its own breakeven - and why W=1R is a trap.

The apply gates read profit factor, expectancy, retention and cost separately.
None of them says how much room is left before a config stops paying, and that
distance is what a small execution degradation eats first. US30 clears every
gate on PF 1.12 while sitting 2.4 points above the line.

The average win is the part that is easy to get wrong. This exit model has no
take-profit, so winners run: USDJPY's average win is 3.6R against a 26.5% win
rate. Assume 1R instead and its breakeven reads 58% rather than 24%, which
inverts the verdict on a config that is actually (narrowly) profitable - the
mistake several outside analyses of this system made.
"""
from __future__ import annotations

import pytest


def _margin(win_rate: float, pf: float, expectancy: float):
    """The endpoint's arithmetic, kept here so the algebra itself is pinned."""
    w = win_rate / 100.0
    ratio = pf * (1 - w) / w
    loss = expectancy / (w * ratio - (1 - w))
    win = ratio * loss
    breakeven = loss / (win + loss) * 100.0
    return win, loss, breakeven, win_rate - breakeven


# Live holdout figures, 2026-08-10.
@pytest.mark.parametrize("symbol,wr,pf,exp,want_win,want_be", [
    ("USDJPY", 26.5, 1.14, 0.117, 3.60, 24.0),
    ("US30",   32.4, 1.12, 0.072, 2.07, 30.0),
    ("XAUUSD", 26.2, 1.61, 0.451, 4.54, 18.1),
    ("USDCHF", 78.9, 2.38, 0.270, 0.59, 61.1),
    ("GBPUSD", 54.8, 2.09, 0.468, 1.64, 36.7),
])
def test_reproduces_the_live_numbers(symbol, wr, pf, exp, want_win, want_be):
    win, _loss, be, _margin_pp = _margin(wr, pf, exp)
    assert win == pytest.approx(want_win, abs=0.02)
    assert be == pytest.approx(want_be, abs=0.15)


def test_a_high_win_rate_config_needs_a_high_win_rate_to_break_even():
    # USDCHF wins 79% of the time but its average win is smaller than its
    # average loss, so it needs 61% just to stand still. A high win rate is
    # not by itself margin.
    win, loss, be, margin = _margin(78.9, 2.38, 0.270)
    assert win < loss
    assert be > 60
    assert margin > 15          # still comfortable, but not because of the 79%


def test_a_low_win_rate_config_can_have_the_widest_margin():
    # XAUUSD wins 26% and has the second-widest margin in the book, because
    # its winners run to 4.5R. The two facts are not in tension.
    _win, _loss, be, margin = _margin(26.2, 1.61, 0.451)
    assert be < 20
    assert margin > 8


def test_assuming_a_one_r_winner_inverts_the_verdict():
    """The specific error to guard against."""
    win, _loss, be, margin = _margin(26.5, 1.14, 0.117)   # USDJPY, real W
    assert win == pytest.approx(3.60, abs=0.02)
    assert margin > 0                                      # actually profitable

    naive_breakeven = (1 + 0.162) / (1 + 1.0) * 100        # W assumed 1R, C=0.162R
    assert naive_breakeven == pytest.approx(58.1, abs=0.1)
    assert naive_breakeven - 26.5 > 30                     # would read as hopeless


def test_the_thin_ones_are_the_three_seen_live():
    live = [("US30", 32.4, 1.12, 0.072), ("USDJPY", 26.5, 1.14, 0.117),
            ("US500", 26.8, 1.15, 0.106), ("GBPJPY", 40.3, 1.23, 0.105),
            ("GBPUSD", 54.8, 2.09, 0.468)]
    thin = [s for s, wr, pf, e in live if _margin(wr, pf, e)[3] < 4.0]
    assert thin == ["US30", "USDJPY", "US500"]


def test_margin_widens_with_profit_factor_at_a_fixed_win_rate():
    prev = None
    for pf in (1.1, 1.3, 1.6, 2.0):
        margin = _margin(35.0, pf, 0.2)[3]
        if prev is not None:
            assert margin > prev
        prev = margin
