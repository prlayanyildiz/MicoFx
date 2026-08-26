"""Retired family helpers must not return. ``ensure_terminal_process`` stays.

trix / delta_proxy / zscore had no remaining production caller after trix_flip
and flow_rev left. If they come back they will be searched again.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import micofx.indicators as ind

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_retired_indicator_helpers_are_gone():
    for name in ("trix", "delta_proxy", "zscore", "macd", "macd_periods"):
        assert not hasattr(ind, name), name


def test_retired_kivanc_losers_are_gone():
    """26.08 holdout: alpha_trend unmeasurable (7 trades < 12), mavilim
    negative (GER -20.2 R / PF 0.92). ichimoku stayed - it passed the gate.
    """
    from micofx.models import STRATEGIES
    from micofx.strategy import _FAMILIES

    for name in ("alpha_trend_rsi", "mavilim_w"):
        assert not hasattr(ind, name), name
    for name in ("alpha_trend", "mavilim"):
        assert name not in STRATEGIES, name
        assert name not in _FAMILIES, name
    assert "ichimoku" in STRATEGIES and "ichimoku" in _FAMILIES


def test_never_applied_scan_waste_is_gone():
    """26.08 opt history: st_trend 1/0 apply, macd_flip 5/0 apply, neither
    live. Each still ate a full max_combos slot per TF. ichimoku stays -
    it cleared the same holdout gate (GER +27.9 R).
    """
    from micofx.models import OPT_FIELDS, STRATEGIES
    from micofx.strategy import _FAMILIES, IndicatorCache, Params

    for name in ("st_trend", "macd_flip"):
        assert name not in STRATEGIES, name
        assert name not in _FAMILIES, name
    for field in ("macd_fast", "macd_slow", "macd_signal"):
        assert field not in OPT_FIELDS, field
        assert field not in Params.__dataclass_fields__
    assert not hasattr(IndicatorCache, "macd")
    assert "ichimoku" in STRATEGIES
    assert len(STRATEGIES) == 11


def test_autostart_is_a_real_feature_not_a_stub():
    """run.py reads autostart_mt5 and calls ensure_terminal_process."""
    from micofx.mt5client import MT5Client
    src = inspect.getsource(MT5Client.ensure_terminal_process)
    assert "terminal_path" in src
    run = (Path(__file__).resolve().parents[1] / "run.py").read_text(encoding="utf-8")
    assert "autostart_mt5" in run
    assert "ensure_terminal_process" in run
