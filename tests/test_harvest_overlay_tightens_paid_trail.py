"""Harvest overlay tightens trail_step after a paid R, without searching it.

NAS100 live 1.0/1.8 kept 0.32 of winner MFE: the trail sat 1.8 ATR behind
the close. GER40 already had partial_at_r=1.5 and still left 12 R on
winners — the remaining two-thirds still trailed 2.2 ATR back. XAUUSD
2.0/0.4 kept 0.80. This overlay copies that tight step once harvest_at_r
is reached. Default 0 is a no-op so existing stamps stay bit-identical.
Not an OPT_FIELD. Not EXIT_RISK (same door as BE / partial).
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx import engine as engine_mod
from micofx.exits import harvest_trail_step, overlay_stop
from micofx.models import EXIT_RISK_FIELDS, OPT_FIELDS, SymbolConfig
from micofx.strategy import Params
from micofx.web.app import _SYMBOL_RISK_BOUNDS


def _kw(**extra):
    base = {
        "is_buy": True, "entry": 100.0, "ref": 102.0, "atr": 1.0,
        "trail_start_atr": 1.0, "trail_step_atr": 1.8, "trail_mode": "atr",
        "struct_sl": None, "breakeven_at_r": 0.0, "original_risk": 1.0,
    }
    base.update(extra)
    return base


def test_harvest_off_is_the_old_overlay():
    assert overlay_stop(**_kw()) == pytest.approx(100.2)


def test_harvest_tightens_step_once_paid():
    # 2R open, 1.8-step trail would sit at 100.2; 0.4-step harvest at 101.6.
    assert overlay_stop(**_kw(harvest_at_r=1.5, harvest_step_atr=0.4)) == pytest.approx(101.6)


def test_harvest_does_not_fire_before_the_r_gate():
    # 1.2R: trail already armed (start 1.0) but harvest is 1.5. Keep 1.8 step.
    assert overlay_stop(**_kw(ref=101.2, harvest_at_r=1.5,
                              harvest_step_atr=0.4)) == pytest.approx(99.4)


def test_harvest_can_arm_before_trail_start():
    # XAU-style start 2.0, but overlay off on gold. When on: 1.6R arms 0.4 step.
    assert overlay_stop(**_kw(
        ref=101.6, trail_start_atr=2.0, trail_step_atr=1.8,
        harvest_at_r=1.5, harvest_step_atr=0.4,
    )) == pytest.approx(101.2)


def test_harvest_and_be_take_the_tighter_of_the_two():
    # BE at entry 100, harvest trail 101.6 — keep 101.6.
    assert overlay_stop(**_kw(
        harvest_at_r=1.5, harvest_step_atr=0.4, breakeven_at_r=1.5,
    )) == pytest.approx(101.6)


def test_zero_defaults_are_off_and_not_search_axes():
    assert SymbolConfig(symbol="NAS100", magic=1).harvest_at_r == 0.0
    assert SymbolConfig(symbol="NAS100", magic=1).harvest_step_atr == 0.0
    assert Params().harvest_at_r == 0.0
    assert Params().harvest_step_atr == 0.0
    assert "harvest_at_r" not in OPT_FIELDS
    assert "harvest_step_atr" not in OPT_FIELDS
    assert "harvest_at_r" not in EXIT_RISK_FIELDS
    assert "harvest_step_atr" not in EXIT_RISK_FIELDS
    assert "harvest_at_r" not in inspect.getsource(Params.key)
    lo, hi, inclusive = _SYMBOL_RISK_BOUNDS["harvest_at_r"]
    assert lo == 0.0 and hi == 5.0 and inclusive is True
    lo, hi, inclusive = _SYMBOL_RISK_BOUNDS["harvest_step_atr"]
    assert lo == 0.0 and hi == 20.0 and inclusive is True


def test_both_callers_pass_harvest_into_overlay_and_min_step():
    eng = inspect.getsource(engine_mod.Engine._update_stop)
    sim = inspect.getsource(backtest.simulate)
    assert "harvest_at_r" in eng and "harvest_step_atr" in eng
    assert "harvest_at_r" in sim and "harvest_step_atr" in sim
    assert "harvest_trail_step" in eng and "harvest_trail_step" in sim


def test_min_step_uses_the_tight_step_once_paid():
    assert harvest_trail_step(
        trail_step_atr=1.8, harvest_at_r=1.5, harvest_step_atr=0.4,
        profit=2.0, original_risk=1.0) == pytest.approx(0.4)
    assert harvest_trail_step(
        trail_step_atr=1.8, harvest_at_r=1.5, harvest_step_atr=0.4,
        profit=1.2, original_risk=1.0) == pytest.approx(1.8)
    assert harvest_trail_step(
        trail_step_atr=1.8, harvest_at_r=0.0, harvest_step_atr=0.4,
        profit=2.0, original_risk=1.0) == pytest.approx(1.8)
