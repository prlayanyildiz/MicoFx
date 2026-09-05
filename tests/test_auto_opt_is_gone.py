"""The CALENDAR and DECAY triggers are gone. The quarantine queue is not.

The old first line read "Automatic search is operator-only", which is false and
was the most misleading sentence in the test suite: it is the file an engineer
greps to answer "does anything auto-optimise?". Something does.
``Supervisor._queue_reoptimization`` calls ``optimizer.start(..., apply_best=
True, source="quarantine")`` (supervisor.py), reached unconditionally from
``review()`` - so a quarantined symbol can be re-searched AND have the winner
applied to it live, with no operator in the loop. This file's own
``test_supervisor_does_not_restore_decay_or_calendar_auto_search`` asserts that
call is present, so the docstring contradicted the assertion three lines below
it.

What is actually pinned here: no calendar trigger, no decay trigger, no panel
dial for either. That is a narrower claim than the old sentence and it is true.

Whether the quarantine path SHOULD auto-apply is a live question, not settled
here - and today it is moot in practice, because supervisor.enabled is false so
review() never runs. Corrected 05.09.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import READABLE_TIMEFRAMES, SystemConfig
from micofx.supervisor import DEFAULTS
from tests.retired_lexicon import RETIRED_TIMEFRAMES

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
    # A tripwire, not a permissive allow-list. This read
    # ``tf in ("M5","M15","M30")`` until 05.09 - it kept passing after M5 was
    # retired and would have kept passing if M5 came back, so it could not
    # detect the thing it looks like it is checking.
    for tf in READABLE_TIMEFRAMES:
        assert tf not in RETIRED_TIMEFRAMES, tf
    assert list(READABLE_TIMEFRAMES) == ["M15", "M30"]
