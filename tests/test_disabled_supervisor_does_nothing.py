"""Off means off.

The supervisor has two ways of acting on the account: refusing an entry
(``gate``) and replacing a live config (``_queue_reoptimization``). Both used
to keep working while ``enabled`` was False.

Quarantine was enforced deliberately - a breaker earned by realised results is
not a discretionary opinion. Sound reasoning, but it is not what the switch
says: an operator who turns the layer off and still finds symbols refused by
it has a control that does not control anything, and no way to tell that from
a bug somewhere else.

The re-optimisation path was the louder leak, and nobody had argued for it: a
disabled supervisor was still starting searches and replacing configs in the
live book.

Reviews still run while disabled, so the panel keeps showing what the
supervisor *would* do. It just does not do it.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor, SymbolVerdict

NOW = time.time()


class _Opt:
    def __init__(self):
        self.busy = False
        self.started: list = []

    def start(self, symbols, apply_best=True):
        self.started = list(symbols)


class _Store:
    """``enabled`` is a property over the persisted settings row."""

    def __init__(self, enabled: bool):
        self.symbols: dict = {}
        self._enabled = enabled

    def get_setting(self, key, default=None):
        if key == "supervisor":
            return {**DEFAULTS, "enabled": self._enabled}
        return default

    def set_setting(self, key, value):
        pass


def _sup(enabled: bool):
    s = object.__new__(Supervisor)
    s._lock = threading.RLock()
    s.verdicts = {}
    s.notes = []
    s.reopt_queue = []
    s.risk_scale = 1.0
    s.optimizer = _Opt()
    s.store = _Store(enabled)
    assert s.enabled is enabled
    return s


def _cfgs(**kw):
    c = dict(DEFAULTS)
    c.update(kw)
    return c


def _quarantined(sup, symbol="NAS100"):
    sup.verdicts[symbol] = SymbolVerdict(
        symbol=symbol, state="quarantine", risk_scale=0.0,
        quarantine_until=NOW + 3600, reason="PF 0.40 cok dusuk")
    return SymbolConfig(symbol=symbol)


class TestTheGate:
    def test_a_quarantine_does_not_block_while_disabled(self):
        sup = _sup(enabled=False)
        cfg = _quarantined(sup)

        allowed, reason, scale = sup.gate(cfg, NOW)

        assert allowed is True, "a disabled layer must not refuse an entry"
        assert reason == ""
        assert scale == 1.0

    def test_a_quarantine_still_blocks_while_enabled(self):
        """The breaker itself is untouched - only the switch changed."""
        sup = _sup(enabled=True)
        cfg = _quarantined(sup)

        allowed, reason, scale = sup.gate(cfg, NOW)

        assert allowed is False
        assert scale == 0.0
        assert "karantina" in reason

    def test_watch_sizing_does_not_apply_while_disabled(self):
        sup = _sup(enabled=False)
        sup.verdicts["JPN225"] = SymbolVerdict(symbol="JPN225", state="watch",
                                               risk_scale=0.6)

        allowed, _, scale = sup.gate(SymbolConfig(symbol="JPN225"), NOW)

        assert allowed is True
        assert scale == 1.0

    def test_the_portfolio_drawdown_scale_does_not_apply_while_disabled(self):
        sup = _sup(enabled=False)
        sup.risk_scale = 0.4

        _, _, scale = sup.gate(SymbolConfig(symbol="GER40"), NOW)

        assert scale == 1.0

    def test_an_unknown_symbol_is_allowed_either_way(self):
        for enabled in (True, False):
            sup = _sup(enabled=enabled)
            allowed, _, _ = sup.gate(SymbolConfig(symbol="NEW"), NOW)
            assert allowed is True


class TestTheReoptimiser:
    def _wire(self, sup, state="quarantine"):
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 100 * 3600,
                           enabled=True)
        sup.store.symbols = {"NAS100": cfg}
        sup.verdicts = {"NAS100": SymbolVerdict(symbol="NAS100", state=state)}
        return cfg

    def test_a_disabled_layer_does_not_replace_a_live_config(self):
        """The louder leak: a search started and applied with AI switched off."""
        sup = _sup(enabled=False)
        self._wire(sup)

        sup._queue_reoptimization(_cfgs())

        assert sup.optimizer.started == []
        assert sup.reopt_queue == []

    def test_an_enabled_layer_still_queues_it(self):
        sup = _sup(enabled=True)
        self._wire(sup)

        sup._queue_reoptimization(_cfgs())

        assert sup.optimizer.started == ["NAS100"]


@pytest.mark.parametrize("state", ["quarantine", "watch", "ok", "idle"])
def test_no_state_leaks_through_the_switch(state):
    """Whatever the verdict says, a disabled layer neither blocks nor resizes."""
    sup = _sup(enabled=False)
    sup.verdicts["X"] = SymbolVerdict(symbol="X", state=state, risk_scale=0.0,
                                      quarantine_until=NOW + 3600)

    allowed, reason, scale = sup.gate(SymbolConfig(symbol="X"), NOW)

    assert (allowed, reason, scale) == (True, "", 1.0)
