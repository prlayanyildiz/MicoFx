"""The ceiling and the reading compared against it must belong to the same leg.

``portfolio-gates`` already picks the binding ceiling correctly - the tighter of
the primary's ``max_spread_atr`` and the secondary's, naming which leg owns it
in ``ceiling_leg``. What it compared that ceiling against was
``state.spread_atr``, and the engine builds that number from the PRIMARY's ATR:

    state.spread_atr = tick["spread"] / state.atr

The two legs routinely run different timeframes, so their ATRs are different
numbers. ``_try_entry`` knows this and gates the secondary on ``state.sec_atr``;
the panel did not, and compared a primary-ATR ratio against a secondary-owned
ceiling.

Live when this was found: seven of ten symbols had a secondary-owned ceiling and
five of those ran the secondary on a different timeframe - FRA40 M30/H1, GER40
M15/H1, NAS100 M15/H1, US30 M15/H1, SpotBrent H1/M5. The error is directional
and goes both ways. A secondary on the higher timeframe has the larger ATR, so
its true ratio is SMALLER than the panel showed and the breach was overstated;
FRA40 was reported as failing "tavan" on that basis, repeatedly, across the
day's reviews. SpotBrent's secondary runs M5 against an H1 primary, where the
ATR is far smaller and the panel understated the ratio instead.

The engine's own numbers are unaffected - it was always gating each leg on that
leg's ATR. This is the analysis view catching up with what the engine does.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _System:
    slippage_points = 20

    def to_dict(self):
        return {}


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, k, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, s, n):
        return []


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None

    def resolve(self, s):
        return s

    def tick(self, s):
        return None


class _State:
    def __init__(self, spread=0.0, atr=0.0, sec_atr=0.0, session_open=True):
        self.spread = spread
        self.atr = atr
        self.sec_atr = sec_atr
        self.spread_atr = (spread / atr) if atr > 0 else 0.0
        self.session = {"open": session_open}


class _Supervisor:
    def __init__(self):
        self.settings = {"lookback_days": 30}

    def status(self):
        return {"symbols": []}


class _Engine:
    def __init__(self, states):
        self.states = states
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}
        self.supervisor = _Supervisor()


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25

    def apply(self, *a, **k):
        return {"ok": True}


def _cfg(primary_ceiling: float, secondary_ceiling: float | None,
         sec_tf: str = "H1") -> SymbolConfig:
    c = SymbolConfig(symbol="FRA40", magic=1, timeframe="M30", strategy="burst")
    c.max_spread_atr = primary_ceiling
    if secondary_ceiling is not None:
        # has_secondary() needs the switch too; all ten live symbols carry it.
        c.ensemble_enabled = True
        c.secondary_strategy = "dual_t3"
        c.secondary_timeframe = sec_tf
        c.secondary_params = {"max_spread_atr": secondary_ceiling}
    c.opt_summary = {"holdout_days": 30.0,
                     "holdout": {"trades": 400, "expectancy": 0.30,
                                 "cost_per_trade_r": 0.05}}
    return c


def _row(cfg, state):
    tc = TestClient(create_app(_Store([cfg]), _Client(), _Engine({"FRA40": state}),
                               _Optimizer()))
    return tc.get("/api/analysis/portfolio-gates").json()["rows"][0]


# FRA40's live shape: spread 0.0861 of the primary M30 ATR, secondary on H1
# whose ATR is twice as large, so the secondary's own ratio is half that.
SPREAD = 8.61
ATR_M30 = 100.0
ATR_H1 = 200.0


# ------------------------------------------------------------- the defect

def test_a_secondary_ceiling_is_judged_against_the_secondary_atr():
    row = _row(_cfg(0.18, 0.08), _State(SPREAD, ATR_M30, ATR_H1))
    assert row["ceiling_leg"] == "secondary"
    assert row["spread_atr_now"] == pytest.approx(SPREAD / ATR_H1, abs=1e-4), (
        "ikincil tavan primary ATR'siyle kiyaslaniyor")


def test_the_overstated_breach_disappears():
    """0.0861 against a 0.08 ceiling reads as a breach on the primary's ATR;
    on the secondary's own it is 0.043 and there is no breach."""
    row = _row(_cfg(0.18, 0.08), _State(SPREAD, ATR_M30, ATR_H1))
    assert "tavan" not in row["fails"]


def test_an_understated_breach_appears():
    """SpotBrent's shape: secondary on M5 against an H1 primary, so the
    secondary's ATR is the smaller one and the true ratio is larger.

    On the primary's ATR the reading is 0.043 and clears a 0.05 ceiling; on the
    secondary's own it is 0.086 and does not. The breach was invisible.
    """
    row = _row(_cfg(0.18, 0.05, sec_tf="M5"), _State(SPREAD, ATR_H1, ATR_M30))
    assert SPREAD / ATR_H1 < 0.05 < SPREAD / ATR_M30, "senaryo gizlenmis ihlali kurmali"
    assert row["spread_atr_now"] == pytest.approx(SPREAD / ATR_M30, abs=1e-4)
    assert "tavan" in row["fails"]


# --------------------------------------------------- what must keep working

def test_a_primary_owned_ceiling_still_uses_the_primary_atr():
    row = _row(_cfg(0.05, 0.20), _State(SPREAD, ATR_M30, ATR_H1))
    assert row["ceiling_leg"] == "primary"
    assert row["spread_atr_now"] == pytest.approx(SPREAD / ATR_M30, abs=1e-4)
    assert "tavan" in row["fails"]


def test_a_symbol_with_no_secondary_is_unchanged():
    row = _row(_cfg(0.05, None), _State(SPREAD, ATR_M30, 0.0))
    assert row["ceiling_leg"] == "primary"
    assert row["spread_atr_now"] == pytest.approx(SPREAD / ATR_M30, abs=1e-4)


def test_both_legs_on_one_timeframe_read_the_same_either_way():
    """UK100's shape - same TF both legs, so nothing moves."""
    row = _row(_cfg(0.12, 0.08), _State(SPREAD, ATR_M30, ATR_M30))
    assert row["spread_atr_now"] == pytest.approx(SPREAD / ATR_M30, abs=1e-4)


def test_a_missing_secondary_atr_falls_back_rather_than_dividing_by_zero():
    """sec_atr is cleared when the ensemble is switched off mid-flight."""
    row = _row(_cfg(0.18, 0.08), _State(SPREAD, ATR_M30, 0.0))
    assert row["spread_atr_now"] == pytest.approx(SPREAD / ATR_M30, abs=1e-4)


def test_no_state_at_all_reports_nothing_rather_than_failing():
    tc = TestClient(create_app(_Store([_cfg(0.18, 0.08)]), _Client(),
                               _Engine({}), _Optimizer()))
    row = tc.get("/api/analysis/portfolio-gates").json()["rows"][0]
    assert row["spread_atr_now"] is None
    assert "tavan" not in row["fails"]
