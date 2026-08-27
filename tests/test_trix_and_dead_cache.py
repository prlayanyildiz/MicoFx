"""trix_flip retired 14.08. ``trix_length`` kept the same three seats flow_* had.

``compute()`` never reads ``p.trix_length``. ``from_dict`` skips unknown keys.
The axis still sat in OPT_FIELDS, Params.key and required_bars.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import OPT_FIELDS, STRATEGIES, SymbolConfig
from micofx.strategy import IndicatorCache, Params, compute, required_bars


def test_opt_fields_do_not_search_trix_length():
    assert "trix_length" not in OPT_FIELDS


def test_params_key_ignores_a_stale_trix_length():
    a = Params.from_config(SymbolConfig.from_dict(
        {"symbol": "XAUUSD", "magic": 1, "trix_length": 8}))
    b = Params.from_config(SymbolConfig.from_dict(
        {"symbol": "XAUUSD", "magic": 1, "trix_length": 30}))
    assert a.key() == b.key()
    assert "trix_length" not in inspect.getsource(Params.key)


def test_an_old_row_with_trix_length_still_loads():
    cfg = SymbolConfig.from_dict({
        "symbol": "FRA40", "magic": 2, "trix_length": 14,
    })
    assert cfg.symbol == "FRA40"
    assert not hasattr(cfg, "trix_length")


def test_required_bars_does_not_depend_on_trix_length():
    assert "trix_length" not in inspect.getsource(required_bars)
    # Retired term was trix_length*15 = 210 at the shipped default (14).
    # mtf_pullback forces htf to 6, so t3_length*20*6 = 720 and 210 never
    # bound. (t3_stoch was the subject here until it retired 27.08.)
    assert required_bars(Params(strategy="mtf_pullback")) == 720


def test_the_panel_does_not_edit_trix_length():
    js = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static" / "app.js"
          ).read_text(encoding="utf-8")
    assert "trix_length" not in js


def test_indicator_cache_has_no_retired_family_helpers():
    for name in ("flow", "delta", "trix", "macd"):
        assert not hasattr(IndicatorCache, name), name


def test_every_living_family_still_computes_without_those_helpers():
    n = 200
    close = 100.0 + np.linspace(0, 1, n)
    high, low, open_ = close + 0.2, close - 0.2, close.copy()
    times = np.arange(n, dtype=np.int64) * 300
    cache = IndicatorCache(high, low, close, times, 300, open_, np.ones(n), np.zeros(n))
    assert sorted(STRATEGIES) == sorted(
        ["mtf_pullback", "burst", "dual_t3",
         "t3_flip", "stoch_flip",
         "parabolic_flip", "aroon_flip",
         "ichimoku"])
    for family in STRATEGIES:
        sig = compute(cache, Params(strategy=family))
        assert sig.buy.size == n and sig.sell.size == n
