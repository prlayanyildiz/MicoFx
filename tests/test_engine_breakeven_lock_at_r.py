"""Live stop locks at entry once open profit reaches breakeven_at_r R.

Trail is independent: a wide trail_step (GER40 2.2 vs SL 1.0) does not
reach entry until 2.2 R, so a trade can print +1.5 R and still die at -1 R.
The lock jumps the stop to entry at the threshold without waiting for the
trail, and without pulling a trail that is already past entry.

Default 0 is off. 1.5 is the BE-1 holdout threshold (no symbol worse).
0.5 is not used: BE-2 validation picked it on GER40 and holdout lost 32 R.
Not an OPT_FIELD — search budget for BE-3 is unpaid.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_trail_retry_within_bar import ATR, _Bars, _Client, _engine, _pos

from micofx.models import OPT_FIELDS, SymbolConfig
from micofx.strategy import Params
from micofx.web.app import _SYMBOL_RISK_BOUNDS


class _Cfg:
    symbol = "GER40"
    magic = 7
    timeframe = "M5"
    sl_atr_mult = 1.0
    trail_start_atr = 3.0   # trail has not armed at +1.6 ATR
    trail_step_atr = 2.2    # would reach entry only at +2.2 R
    trail_mode = "atr"
    trail_lookback = 5
    breakeven_at_r = 1.5


def test_not_a_search_axis():
    assert "breakeven_at_r" not in OPT_FIELDS
    assert "breakeven_at_r" not in inspect.getsource(Params.key)


def test_zero_is_the_dataclass_default():
    assert SymbolConfig(symbol="XAUUSD", magic=1).breakeven_at_r == 0.0
    assert Params().breakeven_at_r == 0.0


def test_params_from_config_carries_it():
    cfg = SymbolConfig(symbol="GER40", magic=1, breakeven_at_r=1.5)
    assert Params.from_config(cfg).breakeven_at_r == 1.5


def test_api_zero_is_legal_and_half_r_is_not_the_ceiling():
    """0 disables; 1.5 is in range; 0.5 is legal to type but not what we apply."""
    lo, hi, inclusive = _SYMBOL_RISK_BOUNDS["breakeven_at_r"]
    assert lo == 0.0 and inclusive
    assert hi >= 1.5
    assert 0.5 < hi


def test_lock_jumps_to_entry_before_the_trail_has_armed():
    # Bar closed at 101.6 = +1.6 R. Trail starts at 3.0 ATR, so it has not
    # produced a target. Without the lock the stop stays at the hard SL (99).
    client = _Client(bid=101.6, min_stop=0.1)
    eng = _engine(client)
    pos = _pos(sl=99.0, entry=100.0)
    assert eng._update_stop(_Cfg(), pos, ATR, _Bars(101.6)) is True
    assert client.modifies == [pytest.approx(100.0)]
    assert pos["sl"] == pytest.approx(100.0)


def test_below_threshold_the_hard_stop_stays():
    client = _Client(bid=101.4, min_stop=0.1)
    eng = _engine(client)
    pos = _pos(sl=99.0, entry=100.0)
    eng._update_stop(_Cfg(), pos, ATR, _Bars(101.4))  # +1.4 R < 1.5
    assert client.modifies == []
    assert pos["sl"] == 99.0


def test_zero_leaves_the_wide_trail_in_charge():
    client = _Client(bid=101.6, min_stop=0.1)
    eng = _engine(client)
    cfg = _Cfg()
    cfg.breakeven_at_r = 0.0
    pos = _pos(sl=99.0, entry=100.0)
    eng._update_stop(cfg, pos, ATR, _Bars(101.6))
    assert client.modifies == []


def test_a_trail_already_past_entry_is_not_pulled_back():
    # Close 104, trail_start 0.5, step 1.6 → trail wants 102.4. Lock at 1.0 R
    # must keep 102.4, not drag it back to 100.
    class _TrailCfg(_Cfg):
        trail_start_atr = 0.5
        trail_step_atr = 1.6
        breakeven_at_r = 1.0

    client = _Client(bid=104.0, min_stop=0.1)
    eng = _engine(client)
    pos = _pos(sl=99.0, entry=100.0)
    eng._update_stop(_TrailCfg(), pos, ATR, _Bars(104.0))
    assert client.modifies == [pytest.approx(102.4)]
