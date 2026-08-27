"""A config cannot be judged on trades it was not alive to make.

``portfolio-gates`` compared two numbers drawn from different populations:

  * ``expected`` = this config's holdout trade rate, projected across the whole
    review window (``window_days``, live 30).
  * ``actual``   = every live trade on the symbol inside that window - most of
    them made by whatever configs ran BEFORE this one.

Those only describe the same thing once the config has been live for the full
window. Nine of the ten live configs were younger than forty-eight hours when
this was found, so it was the normal state rather than an edge case.

US2000 is the case that exposed it. Its config was three and a half hours old,
its holdout implied 100.8 trades over thirty days, and thirty days of history
held five - read as a 5% fill rate and flagged ``siklik``. Scaled instead to the
time the config had actually run, the same two numbers say it traded roughly ten
times FASTER than the holdout rate. Every one of the ten symbols inverts the
same way. Neither figure is trustworthy: ``actual`` is not restricted to the
config's lifetime either, and the supervisor hands over an aggregate count with
no per-trade times to restrict it with. So the reading is withheld rather than
repaired, and ``fill_measurable`` says which of the two it is - a blank that
means "too young to compare" must not read as a zero.

``thin_sample``, the settling hold in ``optimizer.reject_reason`` and the
supervisor's ``watch_min_trades`` all already refuse to judge a config on
evidence it did not produce. This is that same rule on the one path that was
still missing it.

Nothing is switched off by this: portfolio-gates is a classification view and
``siklik`` is rendered, never consumed by the engine. What changes is that the
panel stops asserting a ratio it cannot support.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.web.app import create_app

DAY = 86400.0
WINDOW = 30


class _System:
    slippage_points = 20

    def to_dict(self):
        return {}


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
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


class _Supervisor:
    def __init__(self, live_trades):
        self.settings = {"lookback_days": WINDOW}
        self._live = live_trades

    def status(self):
        return {"symbols": [{"symbol": "US2000", "trades": self._live,
                             "state": "ok", "net": 0.0}]}


class _Engine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}
        self.supervisor = _Supervisor(5)


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25

    def apply(self, *a, **k):
        return {"ok": True}


def _row(age_days: float | None, live_trades: int = 5):
    """US2000's live shape: holdout 336 trades over 100 days -> 100.8 per 30."""
    cfg = SymbolConfig(symbol="US2000", magic=1, timeframe="M15",
                       strategy="burst")
    cfg.opt_updated_at = 0.0 if age_days is None else time.time() - age_days * DAY
    cfg.opt_summary = {
        "holdout_days": 100.0,
        "holdout": {"trades": 336, "expectancy": 0.30, "cost_per_trade_r": 0.05},
    }
    engine = _Engine()
    engine.supervisor = _Supervisor(live_trades)
    tc = TestClient(create_app(_Store(cfg), _Client(), engine, _Optimizer()))
    return tc.get("/api/analysis/portfolio-gates").json()["rows"][0]


# ------------------------------------------------------------- the defect

def test_a_config_younger_than_the_window_reports_no_fill_rate():
    row = _row(age_days=3.5 / 24.0)
    assert row["expected_trades"] == 100.8, "senaryo US2000'in oranini kurmali"
    assert row["actual_trades"] == 5
    assert row["fill_rate"] is None, (
        "3.5 saatlik konfig 30 gunluk gecmisle kiyaslaniyor")


def test_that_config_is_not_flagged_for_frequency():
    assert "siklik" not in _row(age_days=3.5 / 24.0)["fails"]


def test_the_blank_is_labelled_rather_than_left_to_look_like_zero():
    row = _row(age_days=3.5 / 24.0)
    assert row["fill_measurable"] is False
    assert row["config_age_days"] == round(3.5 / 24.0, 2)


# --------------------------------------------------- what must keep working

def test_a_config_older_than_the_window_is_still_judged():
    row = _row(age_days=WINDOW + 5)
    assert row["fill_measurable"] is True
    assert row["fill_rate"] == round(5 / 100.8, 3)
    assert "siklik" in row["fails"], "yasi yeten konfig hala siklikten kalabilmeli"


def test_a_config_exactly_at_the_window_counts_as_measurable():
    assert _row(age_days=WINDOW + 0.01)["fill_measurable"] is True


def test_an_old_config_taking_its_trades_passes():
    row = _row(age_days=WINDOW + 5, live_trades=90)
    assert row["fill_rate"] == round(90 / 100.8, 3)
    assert "siklik" not in row["fails"]


def test_a_config_that_was_never_optimised_reports_nothing_rather_than_failing():
    """opt_updated_at is 0 on a seeded config that has never been through the
    optimizer - unknown age must not be read as infinitely old."""
    row = _row(age_days=None)
    assert row["config_age_days"] is None
    assert row["fill_measurable"] is False
    assert row["fill_rate"] is None
    assert "siklik" not in row["fails"]


def test_the_other_gates_are_untouched_by_this():
    """Only the frequency reading is withheld; expectancy and cost still judge
    a young config, because those are measured on the holdout itself."""
    row = _row(age_days=3.5 / 24.0)
    assert row["expectancy_r"] == 0.30
    assert row["cost_per_trade_r"] == 0.05
    assert row["expected_trades"] == 100.8, "beklenen sayi gorunur kalmali"
