"""macd_flip retired 26.08. The swap-order helper left with it.

macd() / macd_periods had no remaining production caller. If they come
back they will be searched again. Old rows carrying macd_fast still load
because from_dict skips unknown keys.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.indicators as ind
from micofx.models import OPT_FIELDS, STRATEGIES, SymbolConfig
from micofx.strategy import IndicatorCache, Params, required_bars


def test_macd_helpers_are_gone():
    assert not hasattr(ind, "macd")
    assert not hasattr(ind, "macd_periods")
    assert not hasattr(IndicatorCache, "macd")


def test_macd_flip_is_not_searchable():
    assert "macd_flip" not in STRATEGIES
    assert "macd_fast" not in OPT_FIELDS
    assert "macd_fast" not in Params.__dataclass_fields__
    assert "macd_fast" not in inspect.getsource(required_bars)


def test_an_old_row_with_macd_fast_still_loads():
    cfg = SymbolConfig.from_dict({
        "symbol": "GER40", "magic": 2, "macd_fast": 26, "macd_slow": 12,
    })
    assert cfg.symbol == "GER40"
    assert not hasattr(cfg, "macd_fast")
