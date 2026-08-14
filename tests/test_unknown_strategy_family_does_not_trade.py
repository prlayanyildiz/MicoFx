"""An unrecognised strategy family must not quietly trade a different one.

``compute`` routed through ``_FAMILIES.get(p.strategy, _t3_stoch)``, so a
config naming a family that does not exist - a renamed or retired one in a
stale row, a typo written straight to the database - went on trading, but as
t3_stoch, with no error and no log line.

Nothing downstream could notice. The panel, the optimizer's holdout and the
supervisor's judgement all still read the configured name, so the symbol would
be scored, compared to its paper record and suspended as if it were running
what it said it was.

Refusing to signal is the safe direction: trading nothing costs an
opportunity, trading something else costs money against a record that cannot
explain it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import strategy as S
from micofx.models import SymbolConfig


def _cache(n=600):
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 0.4, n))
    high = close + 0.3
    low = close - 0.3
    return S.IndicatorCache(close=close, high=high, low=low)


def _params(strategy: str):
    return S.Params.from_config(SymbolConfig(symbol="X", strategy=strategy))


@pytest.fixture(autouse=True)
def _forget_warned():
    S._UNKNOWN_FAMILIES.clear()
    yield
    S._UNKNOWN_FAMILIES.clear()


def test_an_unknown_family_produces_no_entries():
    sig = S.compute(_cache(), _params("belirsiz_aile"))

    assert not sig.buy.any(), "an unknown family must not open a position"
    assert not sig.sell.any()


def test_it_does_not_silently_run_t3_stoch():
    """The old behaviour: the fallback made these two identical."""
    cache = _cache()
    unknown = S.compute(cache, _params("belirsiz_aile"))
    t3 = S.compute(cache, _params("t3_stoch"))

    assert t3.buy.any() or t3.sell.any(), "control: t3_stoch does signal here"
    assert not np.array_equal(unknown.buy, t3.buy)


def test_it_says_so_at_a_level_that_reaches_disk(monkeypatch):
    seen = []
    monkeypatch.setattr(S.LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append((msg, level)))

    S.compute(_cache(), _params("belirsiz_aile"))

    assert seen, "an unusable config must not fail silently"
    msg, level = seen[0]
    assert level == "WARN"
    assert "belirsiz_aile" in msg


def test_it_warns_once_per_name_not_once_per_bar(monkeypatch):
    seen = []
    monkeypatch.setattr(S.LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append(msg))
    cache = _cache()

    for _ in range(5):
        S.compute(cache, _params("belirsiz_aile"))

    assert len(seen) == 1, "the poll loop must not flood the log"


def test_the_status_series_are_still_populated():
    """The live view must keep working - it is how the operator sees the fault."""
    sig = S.compute(_cache(), _params("belirsiz_aile"))

    assert sig.atr.size > 0
    assert np.isfinite(sig.atr[-1])


@pytest.mark.parametrize("name", sorted(S._FAMILIES))
def test_every_real_family_still_routes_to_itself(name):
    cache = _cache()
    assert np.array_equal(S.compute(cache, _params(name)).buy,
                          S._FAMILIES[name](cache, _params(name)).buy)
