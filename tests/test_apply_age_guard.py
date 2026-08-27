"""A config gets the settling time the system already says it should get.

``reopt_min_age_hours`` (48 by default) states a policy: a configuration is not
reconsidered until it has had that long to run. ``Optimizer.reject_reason``
enforces it on apply. Calendar auto-queue is gone (quarantine search only).
``Optimizer.start`` used to skip the age gate, so the full-scan route
replaced configurations a queued reopt would have left alone.

The churn that produces is measurable in the log's 495 applies. Symbols that
made money have settled on one configuration - SpotBrent's last three applies
are all mtf_pullback/H1, US30's all dual_t3/M15, NatGas has used a single config
across seven applies. The symbols that lost money never stopped moving: USDCHF
went through 12 distinct configurations in 23 applies, USDJPY 10 in 15, JPN225
11 in 30. Every family swap discards the live record for that symbol, so it
never reaches ``watch_min_trades`` (25), so the supervisor never gets to throttle
a configuration that is losing - it is replaced before it can be judged.

Guarding the apply rather than the search is deliberate: the search's report is
information and costs nothing to produce, while the apply is what discards the
live evidence. ``force`` remains for the case this was needed today - two full
runs twenty-five minutes apart, because the first searched a grid that turned
out to be broken.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _System:
    max_cost_pct_of_risk = 25.0
    block_high_cost = True


class _Store:
    def __init__(self, supervisor_settings=None):
        self.system = _System()
        self._sup = supervisor_settings if supervisor_settings is not None else {}

    def get_setting(self, key, default=None):
        return self._sup if key == "supervisor" else default

    def opt_params(self):
        return {}


def _opt(force: bool = False, settings=None) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = _Store(settings)
    opt._force_apply = force
    return opt


def _cfg(age_hours: float) -> SymbolConfig:
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, strategy="stoch_flip", timeframe="M15")
    cfg.opt_updated_at = time.time() - age_hours * 3600.0
    cfg.opt_summary = {}          # no incumbent score to compare against
    return cfg


def _best() -> dict:
    return {
        "score": 12.0,
        "positive_ratio": 1.0,
        "holdout": {"trades": 200, "expectancy": 0.30, "net_r": 60.0,
                    "cost_per_trade_r": 0.05, "profit_factor": 1.4, "score": 12.0},
        "validation": {"trades": 100, "net_r": 30.0, "profit_factor": 1.3},
        "selection": {"trades": 300, "net_r": 90.0, "profit_factor": 1.4},
    }


# ------------------------------------------------------------- the policy holds

@pytest.mark.parametrize("age", [0.5, 6.0, 25.0, 47.9])
def test_a_config_younger_than_the_settling_time_is_left_alone(age):
    assert "saat" in _opt().reject_reason(_cfg(age), _best())


@pytest.mark.parametrize("age", [48.0, 60.0, 500.0])
def test_a_config_that_has_had_its_run_can_be_replaced(age):
    assert _opt().reject_reason(_cfg(age), _best()) == ""


def test_the_reason_says_how_old_it_is_and_what_is_required():
    reason = _opt().reject_reason(_cfg(6.0), _best())
    assert "6" in reason and "48" in reason


# --------------------------------------------------------- the operator's exit

def test_force_applies_anyway():
    """Needed today: two full runs twenty-five minutes apart, because the
    first searched a grid that turned out to be broken."""
    assert _opt(force=True).reject_reason(_cfg(0.5), _best()) == ""


# ------------------------------------------------- it follows the user's number

def test_the_configured_settling_time_is_honoured_not_a_hardcoded_one():
    opt = _opt(settings={"reopt_min_age_hours": 6})
    assert opt.reject_reason(_cfg(3.0), _best()) != ""
    assert opt.reject_reason(_cfg(7.0), _best()) == ""


def test_zero_disables_the_guard():
    opt = _opt(settings={"reopt_min_age_hours": 0})
    assert opt.reject_reason(_cfg(0.1), _best()) == ""


# ------------------------------------------------------ what must keep working

def test_a_symbol_never_optimised_is_not_blocked():
    """opt_updated_at 0 means there is nothing to protect."""
    cfg = _cfg(1.0)
    cfg.opt_updated_at = 0.0
    assert _opt().reject_reason(cfg, _best()) == ""


def test_cfg_none_is_not_blocked_by_settling_time():
    """No incumbent to protect - same fact the old _is_improvement(None) wrapper stated."""
    assert _opt().reject_reason(None, _best()) == ""


def test_the_improvement_wrapper_is_gone():
    """It was `return not self.reject_reason(cfg, best)` with no production caller."""
    assert not hasattr(Optimizer, "_is_improvement")
    root = Path(__file__).resolve().parents[1]
    for name in ("AGENTS.md", "MASTER_PROMPT.md"):
        text = (root / name).read_text(encoding="utf-8")
        assert "_is_improvement" not in text, name


def test_a_genuinely_bad_candidate_is_still_refused_on_its_own_merits():
    bad = _best()
    bad["holdout"]["cost_per_trade_r"] = 0.40
    reason = _opt().reject_reason(_cfg(500.0), bad)
    assert "maliyet" in reason and "saat" not in reason
