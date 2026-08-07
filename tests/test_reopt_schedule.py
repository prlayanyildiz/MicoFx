"""Scheduled auto-reopt gates: Saturday weekday default and days<=0 disable."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SystemConfig


def test_auto_reopt_defaults_to_saturday():
    # time.tm_wday: Monday=0 ... Saturday=5
    assert SystemConfig().auto_reopt_weekday == 5


def test_auto_reopt_days_zero_disables_status_enabled_flag():
    # Engine.reopt_status treats days<=0 as interval-disabled even if the
    # master bool is still true - regression for the old max(0.5, 0) clamp
    # that turned "off" into a half-day cadence.
    from micofx.engine import Engine

    class _Sys:
        auto_reopt = True
        auto_reopt_days = 0.0
        auto_reopt_hour = -1
        auto_reopt_weekday = 5

    class _Store:
        system = _Sys()

        def get_setting(self, key, default=None):
            return default

    class _Client:
        pass

    eng = Engine(_Store(), _Client())
    status = eng.reopt_status()
    assert status["enabled"] is False
    assert status["weekday"] == 5
    assert status["every_days"] == 0.0
