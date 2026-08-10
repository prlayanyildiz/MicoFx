"""The scale the panel shows must be the scale the gate applies.

`effective_scale` used to be recomputed in _status_locked as
`risk_scale * verdict.risk_scale`, independently of gate(). With the AI
advisory layer switched OFF that arithmetic still produced 0.4x/0.24x rows -
next to reasons like "kenar dustu" and "lot kisildi" - while _gate_locked was
returning a flat 1.0 for every symbol that was not quarantined. The panel
reported a portfolio being throttled when nothing was being throttled, which
is how an operator concludes the supervisor is holding symbols back.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import Supervisor, SymbolVerdict


class _Store:
    """`Supervisor.settings`/`.enabled` are read-only properties over this."""

    def __init__(self, symbols, supervisor_settings=None):
        self.symbols = symbols
        self.data = {"supervisor": supervisor_settings or {}}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _sup(enabled: bool, risk_scale: float = 0.4) -> Supervisor:
    cfgs = {s: SymbolConfig(symbol=s, magic=900000 + i)
            for i, s in enumerate(("US30", "NAS100", "XAUUSD"))}
    sup = Supervisor.__new__(Supervisor)
    import threading
    sup._lock = threading.RLock()
    # ``enabled``/``settings`` are read-only properties over the store, so the
    # switch is set where the real one lives rather than shadowed on the
    # instance. Only keys present in supervisor.DEFAULTS survive the merge.
    sup.store = _Store(cfgs, {"enabled": enabled, "prefer_strong_on_dd": False})
    sup.risk_scale = risk_scale
    sup.verdicts = {}
    sup.notes = []
    sup.reopt_queue = []
    sup.last_review = 0.0
    assert sup.enabled is enabled, "fixture failed to set the real switch"
    return sup


def _verdict(symbol, state, risk_scale=1.0, quarantine_until=0.0):
    v = SymbolVerdict(symbol=symbol, state=state, reason="test")
    v.risk_scale = risk_scale
    v.quarantine_until = quarantine_until
    v.blocked_hours = []
    v.hour_risk_scales = {}
    return v


def _rows(sup):
    return {r["symbol"]: r for r in sup.status()["symbols"]}


def test_disabled_supervisor_reports_no_throttle():
    """The headline case: AI off means nothing is being held back."""
    sup = _sup(enabled=False, risk_scale=0.4)
    sup.verdicts = {
        "US30": _verdict("US30", "ok", risk_scale=1.0),
        "XAUUSD": _verdict("XAUUSD", "watch", risk_scale=0.6),
    }
    rows = _rows(sup)
    assert rows["US30"]["effective_scale"] == 1.0
    assert rows["XAUUSD"]["effective_scale"] == 1.0, \
        "a watch symbol showed a throttle the disabled gate never applies"
    assert rows["US30"]["gate_allowed"] is True
    assert rows["XAUUSD"]["gate_allowed"] is True


def test_quarantine_still_reports_zero_when_disabled():
    """Quarantine is a hard breaker enforced even with the AI layer off."""
    sup = _sup(enabled=False)
    sup.verdicts = {"NAS100": _verdict("NAS100", "quarantine", risk_scale=0.0,
                                       quarantine_until=time.time() + 3600)}
    row = _rows(sup)["NAS100"]
    assert row["effective_scale"] == 0.0
    assert row["gate_allowed"] is False
    assert "karantina" in row["gate_reason"]


def test_enabled_supervisor_reports_the_real_throttle():
    """With AI on, the number must match what the gate actually multiplies."""
    sup = _sup(enabled=True, risk_scale=0.5)
    sup.verdicts = {"XAUUSD": _verdict("XAUUSD", "watch", risk_scale=0.6)}
    row = _rows(sup)["XAUUSD"]
    assert row["effective_scale"] == 0.3       # 0.5 * 0.6
    assert row["gate_allowed"] is True


def test_the_reported_scale_never_leaves_the_gate_s_clamp():
    """gate() clamps to [0.1, 1.0]; the display used to skip that entirely."""
    sup = _sup(enabled=True, risk_scale=0.05)
    sup.verdicts = {"US30": _verdict("US30", "ok", risk_scale=0.05)}
    row = _rows(sup)["US30"]
    assert row["effective_scale"] == 0.1, "sub-floor scale reported below the clamp"


def test_status_matches_gate_for_every_row():
    """The invariant, stated directly: no row may disagree with the gate."""
    for enabled in (True, False):
        sup = _sup(enabled=enabled, risk_scale=0.4)
        sup.verdicts = {
            "US30": _verdict("US30", "ok", risk_scale=1.0),
            "NAS100": _verdict("NAS100", "quarantine", risk_scale=0.0,
                               quarantine_until=time.time() + 600),
            "XAUUSD": _verdict("XAUUSD", "watch", risk_scale=0.6),
        }
        now = time.time()
        for symbol, row in _rows(sup).items():
            allowed, reason, scale = sup.gate(sup.store.symbols[symbol], now)
            assert row["effective_scale"] == round(scale, 3), f"{symbol} enabled={enabled}"
            assert row["gate_allowed"] == allowed, f"{symbol} enabled={enabled}"
