"""``charge_costs`` decides which configs the search is allowed to pick.

With it off the search never pays the spread, so it can select a config whose
edge is smaller than the spread it will actually pay. Measured 14.08: expected
edge 0.058-0.212 R per trade against a live spread of 0.02-0.27 R, with four
symbols unable to cover their own spread.

It had no control in the panel at all - the only way to change it was the raw
API, so the operator could not act on the finding from the interface that
reports it. A setting that decides what gets traded has to be reachable from
the same place the numbers are.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SystemConfig

APP_JS = (Path(__file__).resolve().parents[1]
          / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def test_charge_costs_has_a_control():
    assert '"charge_costs"' in APP_JS, "the setting must be editable from the panel"


def test_it_is_declared_as_a_boolean():
    m = re.search(r'\{[^{}]*k:\s*"charge_costs"[^{}]*\}', APP_JS, re.S)
    assert m, "charge_costs field definition not found"
    assert 't: "bool"' in m.group(0)


def test_the_control_explains_the_trade_off():
    """A switch this consequential must not be an unlabelled toggle."""
    m = re.search(r'\{[^{}]*k:\s*"charge_costs"[^{}]*\}', APP_JS, re.S)
    assert "hint:" in m.group(0), "no explanation attached"
    assert "kenar" in m.group(0), "the hint must name the edge-vs-spread problem"


def test_the_cost_gate_settings_are_still_there():
    """Adding this must not displace the gate it sits next to."""
    for key in ("block_high_cost", "max_cost_pct_of_risk"):
        assert f'"{key}"' in APP_JS


def test_the_field_exists_on_the_config_it_edits():
    assert hasattr(SystemConfig(), "charge_costs")
