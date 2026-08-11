"""A non-positive EMA length must not crash or silently diverge.

``ema`` builds its smoothing factor as ``2 / (length + 1)`` and was the one
length-taking helper in this module that never clamped - wilder() was fixed
for exactly this, and its comment already asserted that ema defended itself.

Two failure modes, and the quiet one is worse:

    length == -1   ZeroDivisionError, loud and obvious
    length <= -2   a NEGATIVE alpha - no error, just a recursion that
                   oscillates and diverges. Over a gentle 100..110 ramp,
                   ema(x, -2) returns -7.3e22 and flows into signal
                   generation as an ordinary number.
    length == 0    alpha 2.0, outside the (0, 1] range the recursion assumes

Reachable rather than theoretical: ``pull_fast`` is passed to ema() by
_mtf_pullback, and both POST /api/symbols/{symbol} and POST /api/opt/params
accept a negative value with HTTP 200 - the bounds checks there only cover the
exit axes, so nothing between the request and this function says no.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import indicators as ind
from micofx import strategy as S

RAMP = np.linspace(100.0, 110.0, 60)


@pytest.mark.parametrize("length", [-1000, -2, -1, 0])
def test_a_non_positive_length_behaves_like_length_one(length):
    got = ind.ema(RAMP, length)
    assert np.allclose(got, ind.ema(RAMP, 1))


@pytest.mark.parametrize("length", [-1000, -2, -1, 0, 1, 2, 14])
def test_the_output_stays_finite_and_in_range(length):
    got = ind.ema(RAMP, length)
    assert np.all(np.isfinite(got)), f"length={length} sonlu degil"
    # An average of the input can never leave the input's own range.
    assert got.min() >= RAMP.min() - 1e-9
    assert got.max() <= RAMP.max() + 1e-9


def test_the_divergence_case_specifically():
    """The silent one: no exception, just a number 20 orders of magnitude out."""
    assert abs(float(ind.ema(RAMP, -2)[-1])) < 1e4


def test_a_normal_length_is_unchanged():
    """The clamp must not touch the range anything actually uses."""
    for length in (2, 5, 8, 13, 21, 50, 200):
        got = ind.ema(RAMP, length)
        alpha = 2.0 / (length + 1.0)
        expected = RAMP[0]
        for value in RAMP[1:]:
            expected = alpha * value + (1 - alpha) * expected
        assert abs(float(got[-1]) - expected) < 1e-9, length


def test_an_empty_series_is_still_empty():
    assert ind.ema(np.array([], dtype=np.float64), 8).size == 0


# --------------------------------------------- the caller that reaches it

@pytest.mark.parametrize("pull_fast", [-1000, -2, -1, 0])
def test_mtf_pullback_survives_a_hostile_pull_fast(pull_fast):
    close = (100 + np.cumsum(np.sin(np.arange(400) / 7.0))).astype(np.float64)
    cache = S.IndicatorCache(close + 0.5, close - 0.5, close,
                             cost=np.full(400, 0.01))
    params = S.Params(strategy="mtf_pullback")
    params.pull_fast = pull_fast
    signals = S.compute(cache, params)          # used to raise / return garbage
    last = signals.last()
    assert np.isfinite(last["t3"]) and np.isfinite(last["atr"])
    assert not (last["buy"] and last["sell"])


def test_every_length_taking_helper_in_this_module_clamps():
    """wilder()'s comment claims this holds; it did not, so assert it."""
    import re

    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "indicators.py").read_text(encoding="utf-8")
    # The recursive smoothers are the ones where a bad length is unsafe: they
    # turn it into an alpha and feed it back into their own output.
    for name in ("ema", "wilder"):
        match = re.search(rf"^def {name}\(.*?(?=^def )", src, re.M | re.S)
        assert match, name
        assert "max(1, int(length))" in match.group(0), (
            f"{name}() length'i clamp etmiyor")
