"""Quarantine judges the config that is running, and must have a way out.

The losing-streak breaker is what makes a low ``quarantine_losses`` usable at
all. Before this, the loop the operator asked for could not close:

    N losses -> quarantine -> re-optimise -> new config -> release

Three things blocked it, and all three are here:

1. The streak was counted over the whole 30-day window, so a freshly searched
   config inherited the losses of the one it replaced and was re-quarantined on
   the next review before a single trade had tested it.
2. ``_queue_reoptimization`` skipped any symbol whose config was younger than
   ``reopt_min_age_hours`` (48h). A symbol that broke a day after its last apply
   sat quarantined with no attempt to fix it - the age bar is about not churning
   a merely OLD config, but a quarantine is the breaker having already fired.
3. Nothing lifted the quarantine when a new config landed: ``quarantine_until``
   ran the full ``quarantine_hours`` regardless.

Deliberately narrow: only the STREAK is scoped to the current config. PF, the
trade count and the watch bar keep their full window, so a symbol cannot
launder a bad record by churning configs.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor, SymbolVerdict

NOW = time.time()
HOUR = 3600.0


class _SettingsStore:
    """Only what _judge reaches for: settings and the symbol map."""

    def __init__(self) -> None:
        self.symbols: dict = {}

    def get_setting(self, key, default=None):
        return dict(DEFAULTS) if key == "supervisor" else default


def _sup() -> Supervisor:
    import threading

    s = object.__new__(Supervisor)
    s._lock = threading.RLock()
    s.store = _SettingsStore()
    s.verdicts = {}
    s.notes = []
    s.reopt_queue = []
    s.risk_scale = 1.0
    s.optimizer = None
    return s


def _cfgs(**kw):
    c = dict(DEFAULTS)
    c.update(kw)
    return c


def _deal(when: float, net: float) -> dict:
    return {"time": when, "profit": net, "commission": 0.0, "swap": 0.0}


def _judge(sup, cfg, trades, cfgs):
    nets = [d["profit"] for d in trades]
    # _judge computes nets itself from the deal rows; drive it the same way
    # review() does and read the verdict back.
    return sup._judge(cfg, trades, cfgs), nets


class TestStreakIsScopedToTheCurrentConfig:
    def test_losses_from_the_replaced_config_do_not_count(self):
        sup = _sup()
        applied = NOW - 1 * HOUR
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=applied)
        # Four losers under the OLD config, none under the new one.
        trades = [_deal(applied - 600 * i, -5.0) for i in range(4, 0, -1)]

        v, _ = _judge(sup, cfg, trades, _cfgs(quarantine_losses=4))

        assert v.consecutive_losses == 0, "old config's streak must not carry over"
        assert v.state != "quarantine"

    def test_losses_under_the_current_config_do_count(self):
        sup = _sup()
        applied = NOW - 2 * HOUR
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=applied)
        trades = [_deal(applied + 60 * i, -5.0) for i in range(1, 5)]

        v, _ = _judge(sup, cfg, trades, _cfgs(quarantine_losses=4))

        assert v.consecutive_losses == 4
        assert v.state == "quarantine"
        assert v.quarantined_at > 0.0, "the moment it fired must be stamped"

    def test_a_win_still_breaks_the_streak(self):
        sup = _sup()
        applied = NOW - 2 * HOUR
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=applied)
        trades = [_deal(applied + 60, -5.0), _deal(applied + 120, -5.0),
                  _deal(applied + 180, +9.0), _deal(applied + 240, -5.0)]

        v, _ = _judge(sup, cfg, trades, _cfgs(quarantine_losses=4))

        assert v.consecutive_losses == 1
        assert v.state != "quarantine"

    def test_a_never_optimised_symbol_still_counts_its_streak(self):
        """opt_updated_at=0 must not silently disable the breaker."""
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=0.0)
        trades = [_deal(NOW - 60 * i, -5.0) for i in range(4, 0, -1)]

        v, _ = _judge(sup, cfg, trades, _cfgs(quarantine_losses=4))

        assert v.consecutive_losses == 4
        assert v.state == "quarantine"


class TestQuarantineReleasesWhenTheConfigIsReplaced:
    def test_a_new_config_lifts_the_clock(self):
        sup = _sup()
        quarantined = NOW - 1 * HOUR
        # Config applied AFTER the quarantine fired - the re-optimisation the
        # quarantine queued has landed.
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 10 * 60)
        sup.verdicts["NAS100"] = SymbolVerdict(
            symbol="NAS100", state="quarantine",
            quarantine_until=NOW + 11 * HOUR, quarantined_at=quarantined)

        v, _ = _judge(sup, cfg, [_deal(NOW - 30 * HOUR, -5.0)], _cfgs(quarantine_losses=4))

        assert v.state != "quarantine", "a replaced config must not serve the old sentence"
        assert v.quarantine_until == 0.0
        assert v.quarantined_at == 0.0

    def test_the_same_config_serves_its_sentence(self):
        """No config change means the clock still runs - the breaker holds."""
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 5 * HOUR)
        sup.verdicts["NAS100"] = SymbolVerdict(
            symbol="NAS100", state="quarantine",
            quarantine_until=NOW + 11 * HOUR, quarantined_at=NOW - 1 * HOUR)

        v, _ = _judge(sup, cfg, [_deal(NOW - 30 * HOUR, -5.0)], _cfgs(quarantine_losses=4))

        assert v.state == "quarantine"
        assert v.quarantine_until > NOW


class TestTheBreakerCanReachAReoptimisation:
    def _wire(self, sup, cfg, verdict, cfgs):
        class _Opt:
            busy = False
            started: list = []

            def start(self, symbols, apply_best=True):
                type(self).started = list(symbols)

        sup.store = type("S", (), {"symbols": {cfg.symbol: cfg}})()
        sup.optimizer = _Opt()
        sup.verdicts = {cfg.symbol: verdict}
        sup._queue_reoptimization(cfgs)
        return _Opt

    def test_a_quarantine_is_not_blocked_by_the_config_age_bar(self):
        """The gap: a symbol that broke a day after its apply had no way out."""
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 1 * HOUR, enabled=True)
        v = SymbolVerdict(symbol="NAS100", state="quarantine")

        opt = self._wire(sup, cfg, v, _cfgs(reopt_min_age_hours=48))

        assert sup.reopt_queue == ["NAS100"]
        assert opt.started == ["NAS100"]

    def test_a_merely_young_healthy_config_is_still_left_alone(self):
        """The age bar must keep doing its job for everything that is not broken."""
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 1 * HOUR, enabled=True)
        v = SymbolVerdict(symbol="NAS100", state="watch", expected_r=0.5)

        opt = self._wire(sup, cfg, v, _cfgs(reopt_min_age_hours=48))

        assert sup.reopt_queue == []
        assert opt.started == []

    def test_the_retry_cooldown_still_stops_a_tight_loop(self):
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 1 * HOUR, enabled=True)
        v = SymbolVerdict(symbol="NAS100", state="quarantine",
                          last_reopt_attempt=NOW - 60)

        self._wire(sup, cfg, v, _cfgs(reopt_min_age_hours=48,
                                      reopt_retry_cooldown_hours=1.0))

        assert sup.reopt_queue == [], "a quarantine must not re-search every review"


def test_the_option_is_reachable_from_the_panel():
    """The operator has to be able to set this without editing code."""
    app_js = (Path(__file__).resolve().parents[1]
              / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert '"quarantine_losses"' in app_js
    assert '"quarantine_hours"' in app_js
    assert '"auto_reoptimize"' in app_js


@pytest.mark.parametrize("losses,expected", [(3, True), (4, True), (5, False)])
def test_the_threshold_is_honoured_exactly(losses, expected):
    sup = _sup()
    applied = NOW - 2 * HOUR
    cfg = SymbolConfig(symbol="NAS100", opt_updated_at=applied)
    trades = [_deal(applied + 60 * i, -5.0) for i in range(1, 5)]  # 4 losers

    v, _ = _judge(sup, cfg, trades, _cfgs(quarantine_losses=losses))

    assert (v.state == "quarantine") is expected
