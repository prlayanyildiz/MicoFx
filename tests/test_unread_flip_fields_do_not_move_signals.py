"""Payload fields a remaining ungated flip never reads must not move its signals.

t3_flip and ichimoku still ignore leftover ``htf_factor`` / ``adx_min``.
stoch/parabolic/aroon now read those gates; they live in
``test_stoch_flip_respects_trend_and_adx``. AST ``opt_fields_read`` can
miss a dynamic read; this bit-identical check cannot.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.strategy import IndicatorCache, Params, compute, opt_fields_read

FLIP = (
    "t3_flip",
    "ichimoku",
)

# Values a family that *does* call ``_regime`` / ``_trend_gate`` would act on.
POISON = {
    "htf_factor": 12,
    "htf_mode": "t3",
    "adx_min": 25.0,
    "adx_max": 40.0,
    "min_body_ratio": 0.4,
    "atr_pct_min": 0.3,
}


def _cache(n=900):
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 0.4, n))
    high = close + 0.35
    low = close - 0.35
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return IndicatorCache(high=high, low=low, close=close, open_=open_,
                          times=np.arange(n, dtype=np.int64) * 300, tf_seconds=300)


def _params(strategy: str, **overrides):
    return Params.from_config(SymbolConfig(symbol="X", strategy=strategy),
                              **overrides)


@pytest.mark.parametrize("name", FLIP)
def test_flip_family_does_not_read_the_poison_fields(name):
    read = opt_fields_read(name)
    for field in POISON:
        assert field not in read, f"{name} now reads {field}; the bit-identical test would be lying"


@pytest.mark.parametrize("name", FLIP)
def test_poisoning_unread_fields_leaves_flip_signals_bit_identical(name):
    cache = _cache()
    clean = compute(cache, _params(name))
    poisoned = compute(cache, _params(name, **POISON))

    assert clean.buy.any() or clean.sell.any(), f"control: {name} must signal on this series"
    assert np.array_equal(clean.buy, poisoned.buy), f"{name} buy moved after unread poison"
    assert np.array_equal(clean.sell, poisoned.sell), f"{name} sell moved after unread poison"


def test_a_family_that_reads_the_gates_does_move():
    """If this also stayed identical the fixture would not be able to catch a leak.

    The control has to be a family that actually reads POISON's axes.
    dual_t3 calls ``_regime``; the remaining ungated flips (t3_flip,
    ichimoku) do not.
    """
    cache = _cache()
    clean = compute(cache, _params("dual_t3"))
    poisoned = compute(cache, _params("dual_t3", **POISON))

    assert clean.buy.any() or clean.sell.any()
    assert not np.array_equal(clean.buy, poisoned.buy) or not np.array_equal(
        clean.sell, poisoned.sell)
