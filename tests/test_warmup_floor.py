"""The engine must not trade on a signal computed from a warmup stub.

required_bars() states what the indicator stack needs to be trustworthy, and
the bar fetch asks for exactly that. The guard behind it used to accept a flat
60 - 8% of the 720 every family asks for. MT5 populates chart history lazily,
so a symbol can legitimately return far less than was requested during the
first cycles after start-up.

The signals computed on that stub are not weaker versions of the real ones,
they are different ones. Measured on a 4000-bar series, 20 families, 100
sample bars each, comparing the last bar's signal against the same bar with
full history behind it:

    720 bars   0 of 116 real signals disagreed
    360 bars   2
    240 bars   2
    200 bars  24
     60 bars  82        - wrong more often than right

and at 60 bars mtf_pullback, wavetrend_flip and stoch_flip were wrong on
every single signal they produced.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import STRATEGIES
from micofx.strategy import IndicatorCache, Params, compute, required_bars

TF = 300
N = 2500


@pytest.fixture(scope="module")
def series():
    rng = np.random.default_rng(5)
    close = 100 + np.cumsum(rng.normal(0, 0.4, N)) + 4 * np.sin(np.arange(N) / 35)
    return {
        "high": close + 0.5, "low": close - 0.5, "close": close,
        "open_": np.concatenate([[close[0]], close[:-1]]),
        "volume": np.ones(N), "times": np.arange(N, dtype=np.int64) * TF,
    }


def _signals(series, family, start=0):
    s = slice(start, N)
    cache = IndicatorCache(series["high"][s], series["low"][s], series["close"][s],
                           times=series["times"][s], tf_seconds=TF,
                           open_=series["open_"][s], volume=series["volume"][s])
    with np.errstate(all="ignore"):
        sig = compute(cache, Params(strategy=family))
    return bool(np.asarray(sig.buy, bool)[-1]), bool(np.asarray(sig.sell, bool)[-1])


def test_the_floor_is_derived_from_required_bars_not_a_constant():
    """Pins the relationship, so a family raising its lookback moves the floor."""
    need = required_bars(Params())
    assert need >= 240
    assert max(60, need // 2) >= 240, "taban guvenli bolgenin altina dustu"


@pytest.mark.parametrize("family", STRATEGIES)
def test_half_the_required_warmup_reproduces_the_full_history_signal(series, family):
    """At the new floor the last bar's signal matches full history."""
    need = required_bars(Params(strategy=family))
    floor = max(60, need // 2)
    assert _signals(series, family, start=0) == _signals(series, family, start=N - floor)


def test_the_old_floor_was_measurably_wrong(series):
    """The evidence for the change, kept so it cannot be reverted blind.

    At 60 bars the last-bar signal disagrees with full history on families
    that are perfectly stable at the new floor.
    """
    disagreements = 0
    for family in STRATEGIES:
        full = _signals(series, family, start=0)
        if full == _signals(series, family, start=N - 60):
            continue
        disagreements += 1
    assert disagreements > 0, "60 barlik taban artik zararsiz - olcumu gozden gecir"


def test_engine_rejects_a_short_series(monkeypatch, tmp_path):
    """The guard itself, at the call site."""

    from micofx import store as store_module

    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "warm.db")
    from micofx.engine import Engine
    from micofx.store import Store

    need = required_bars(Params())
    served = {"count": 0}

    class _Bars:
        def __init__(self, n):
            self.n = n
            t = np.arange(n, dtype=np.int64) * TF
            c = 100 + np.arange(n) * 0.01
            self.time, self.close = t, c
            self.high, self.low = c + 0.5, c - 0.5
            self.open = c
            self.spread = np.zeros(n)
            self.volume = np.ones(n)
            self.last_closed_time = int(t[-1]) if n else 0

        def __len__(self):
            return self.n

    class _Client:
        connected = True

        def bars(self, symbol, timeframe, count):
            return _Bars(served["count"])

        def positions(self, magic=None, symbol=None):
            return []

        def set_overrides(self, m):
            pass

        def min_stop_distance(self, s):
            return 0.0

        def info(self, s):
            return None

        def resolve(self, s):
            return s

        def tick(self, s):
            return None

        def account(self):
            return {}

        def server_now(self):
            import time
            return time.time()

        def broker_now(self):
            # The clock the new-bar trigger reads. 0.0 is "no tick seen yet",
            # which is what a fake with no feed honestly is - the refresh then
            # falls through to the stale timer, exactly as live does at start-up.
            return 0.0

    from micofx.engine import SymbolState

    store = Store()
    engine = Engine(store, _Client())
    symbol = next(iter(store.symbols))
    cfg = store.symbols[symbol]
    params = Params(strategy=cfg.strategy)
    floor = max(60, need // 2)

    # Below the floor: refused, and the note says how far short it fell.
    served["count"] = floor - 1
    state = SymbolState(symbol)
    assert engine._refresh_signals(cfg, state, params) is False
    assert str(floor) in state.note, state.note
    assert state.bars_ready == floor - 1

    # The old floor is inside the refused range, which is the whole point.
    served["count"] = 60
    state = SymbolState(symbol)
    assert engine._refresh_signals(cfg, state, params) is False

    # At the floor: accepted.
    served["count"] = floor
    state = SymbolState(symbol)
    assert engine._refresh_signals(cfg, state, params) is True
    assert state.bars_ready == floor
