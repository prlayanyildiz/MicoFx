"""Automatic search is operator-only. Calendar and AI queue must not start one."""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import READABLE_TIMEFRAMES, SystemConfig
from micofx.supervisor import DEFAULTS

ROOT = Path(__file__).resolve().parents[1]


def test_system_config_has_no_calendar_reopt_dials():
    names = {f.name for f in SystemConfig.__dataclass_fields__.values()} \
        if hasattr(SystemConfig, "__dataclass_fields__") else set(SystemConfig.__annotations__)
    for key in ("auto_reopt", "auto_reopt_days", "auto_reopt_hour", "auto_reopt_weekday"):
        assert key not in names, key


def test_engine_does_not_schedule_a_search():
    from micofx.engine import Engine
    src = inspect.getsource(Engine)
    assert "_maybe_schedule_reopt" not in src
    assert "source=\"scheduled\"" not in src
    assert "auto_reopt" not in src


def test_supervisor_does_not_restore_decay_or_calendar_auto_search():
    assert "auto_reoptimize" not in DEFAULTS
    assert "reopt_on_decay" not in DEFAULTS
    from micofx.supervisor import Supervisor
    src = inspect.getsource(Supervisor._queue_reoptimization)
    assert "optimizer.start" in src
    assert "reopt_on_decay" not in src


def test_panel_has_no_auto_opt_dials():
    js = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    help_js = (ROOT / "micofx" / "web" / "static" / "field_help.js").read_text(encoding="utf-8")
    for blob in (js, help_js):
        assert "auto_reopt" not in blob
        assert "auto_reoptimize" not in blob
        assert "reopt_on_decay" not in blob
    assert "SuperTrend Donusu" not in js


def test_correlation_unknown_tf_falls_back_to_a_readable_bar():
    src = (ROOT / "micofx" / "web" / "app.py").read_text(encoding="utf-8")
    assert 'else "H1"' not in src
    assert "timeframe: str = \"H1\"" not in src
    assert "/api/analysis/correlation" not in src
    for tf in READABLE_TIMEFRAMES:
        assert tf in ("M5", "M15", "M30")
