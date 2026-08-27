"""A throttle that is switched off must not be reported as a size cut.

``risk_scale`` is the drawdown throttle: the day bleeds, and it falls towards
``risk_scale_floor`` so new entries size down. It is a SOFT layer, and
``_gate_locked`` waives every soft layer in one line:

    if not self.enabled:
        return True, "", 1.0

That return sits ahead of all four places ``self.risk_scale`` is consumed, so
with the AI advisory layer off the throttle multiplies nothing. Quarantine
survives - it is checked before that line, deliberately, being a circuit
breaker earned by realised results rather than an opinion.

``review()`` keeps running either way, so the number keeps being computed, and
the header reported it flat: ``risk_scale: 0.4`` plus a note reading "Gunluk
zarar %7.94 -> lot carpani 0.40". Read plainly that says the book had cut its
size to 40%. It had not - it was opening at full scale, with edge_scale still
pushing proven symbols up to EDGE_MAX (2.2), because that amplifier hangs off
``system.size_by_edge`` and not off the AI switch at all. The amplifier was in
force and the damper was not, and the panel said the opposite.

The per-symbol rows already carry this correction - ``effective_scale`` asks
``_gate_locked`` itself rather than recomputing the arithmetic, and
``hours_enforced`` states whether the hour rules bind. The header kept the old
wording, which is the same defect one level up: this is the fix moving to the
copy that was missed, not a new rule.

Nothing about sizing changes here. Whether the AI layer is on is the operator's
switch; what this fixes is the panel describing a restraint that is not
running.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import Supervisor


class _Store:
    def __init__(self, cfg, enabled):
        self.symbols = {cfg.symbol: cfg}
        # Supervisor.settings is a property merging this over DEFAULTS, so the
        # switch has to be set here rather than assigned on the instance.
        self.data = {"supervisor": {"enabled": enabled}}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _sup(enabled: bool, risk_scale: float = 0.4) -> Supervisor:
    cfg = SymbolConfig(symbol="NAS100", magic=900001)
    sup = Supervisor.__new__(Supervisor)
    sup._lock = threading.RLock()
    sup.store = _Store(cfg, enabled)
    sup.risk_scale = risk_scale
    sup.verdicts = {}
    sup.notes = []
    sup.last_review = 0.0
    sup.optimizer = None
    return sup


# ------------------------------------------------------------- the defect

def test_the_header_says_the_throttle_is_not_in_force_when_ai_is_off():
    assert _sup(enabled=False).status()["risk_scale_enforced"] is False


def test_the_number_is_still_reported_so_it_can_be_read():
    """Withholding it would be its own lie - it is what would apply the moment
    the layer is switched back on."""
    assert _sup(enabled=False).status()["risk_scale"] == 0.4


def test_nothing_is_actually_throttled_while_it_is_off():
    """The claim behind the flag: the gate hands back a flat 1.0."""
    sup = _sup(enabled=False)
    allowed, reason, scale = sup._gate_locked(sup.store.symbols["NAS100"], 0.0)
    assert allowed is True and reason == "" and scale == 1.0


# --------------------------------------------------- what must keep working

def test_the_throttle_is_reported_in_force_when_ai_is_on():
    sup = _sup(enabled=True)
    assert sup.status()["risk_scale_enforced"] is True
    assert sup.status()["risk_scale"] == 0.4


def test_it_really_does_throttle_when_on():
    sup = _sup(enabled=True)
    _, _, scale = sup._gate_locked(sup.store.symbols["NAS100"], 0.0)
    assert scale == 0.4, "acikken carpan gercekten uygulanmali"


def test_an_untroubled_day_reports_enforced_too():
    """The flag is about the switch, not about whether the number bites."""
    sup = _sup(enabled=True, risk_scale=1.0)
    assert sup.status()["risk_scale_enforced"] is True
    assert sup.status()["risk_scale"] == 1.0


def test_the_panel_asks_whether_the_throttle_is_in_force():
    """The API flag was the first half. The header still printed 'kisildi'."""
    js = (Path(__file__).resolve().parents[1]
          / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert "risk_scale_enforced" in js
    assert "carpan uygulanmiyor" in js
