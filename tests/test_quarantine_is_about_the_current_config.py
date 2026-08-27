"""Quarantine judges the config that is running.

The losing-streak breaker is what makes a low ``quarantine_losses`` usable.
A search is operator-started; this file only keeps the sentence honest:

1. The streak is counted on the current config, so a freshly applied
   config does not inherit the previous one's losses.
2. A new ``opt_updated_at`` after the quarantine stamp lifts the clock.
   The same config serves its sentence.

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


class TestQuarantineStartsASearch:
    def _wire(self, sup, cfg, verdict, cfgs):
        class _Opt:
            busy = False
            started: list = []

            def start(self, symbols, apply_best=True, **_kw):
                type(self).started = list(symbols)

        sup.store.symbols = {cfg.symbol: cfg}
        sup.optimizer = _Opt()
        sup.verdicts = {cfg.symbol: verdict}
        sup._queue_reoptimization(cfgs)
        return _Opt

    def test_a_quarantine_starts_a_search(self):
        """A breaker that already fired is not left sitting until the operator."""
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 1 * HOUR, enabled=True)
        v = SymbolVerdict(symbol="NAS100", state="quarantine")

        opt = self._wire(sup, cfg, v, _cfgs(reopt_min_age_hours=48))

        assert opt.started == ["NAS100"]

    def test_a_decayed_watch_does_not_start_a_search(self):
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 1 * HOUR, enabled=True)
        v = SymbolVerdict(symbol="NAS100", state="watch", expected_r=0.5)

        opt = self._wire(sup, cfg, v, _cfgs(reopt_min_age_hours=48))

        assert opt.started == []

    def test_the_retry_cooldown_still_stops_a_tight_loop(self):
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 1 * HOUR, enabled=True)
        v = SymbolVerdict(symbol="NAS100", state="quarantine",
                          last_reopt_attempt=NOW - 60)

        opt = self._wire(sup, cfg, v, _cfgs(reopt_retry_cooldown_hours=1.0))

        assert opt.started == [], "a quarantine must not re-search every review"

    def test_a_failed_start_does_not_burn_the_retry_cooldown(self):
        """last_reopt_attempt used to be stamped before start() ran.

        A busy race or empty-target refuse then silenced the breaker for the
        whole reopt_retry_cooldown_hours even though no search began.
        """
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=NOW - 1 * HOUR, enabled=True)
        v = SymbolVerdict(symbol="NAS100", state="quarantine", last_reopt_attempt=0.0)

        class _Opt:
            busy = False

            def start(self, symbols, apply_best=True, **_kw):
                return {"ok": False, "error": "Optimizasyon zaten calisiyor."}

        sup.store.symbols = {cfg.symbol: cfg}
        sup.optimizer = _Opt()
        sup.verdicts = {cfg.symbol: v}
        sup._queue_reoptimization(_cfgs(reopt_retry_cooldown_hours=1.0))

        assert v.last_reopt_attempt == 0.0


def test_the_option_is_reachable_from_the_panel():
    """The operator has to be able to set this without editing code."""
    app_js = (Path(__file__).resolve().parents[1]
              / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert '"quarantine_losses"' in app_js
    assert '"quarantine_hours"' in app_js
    assert '"auto_reoptimize"' not in app_js


def test_ok_reason_names_both_windows_when_they_differ():
    """Live NAS100: pill says ok, reason says PF 0.54, decision used 37 trades.

    After a release the watch/quarantine bars read the short window; the
    panel PF is still the 30-day book. Same label, two quantities.
    """
    sup = _sup()
    cleared = NOW - 3 * HOUR
    cfg = SymbolConfig(symbol="NAS100")
    sup.verdicts["NAS100"] = SymbolVerdict(
        symbol="NAS100", history_cleared_at=cleared)
    old = [_deal(cleared - 600 * i, -5.0) for i in range(80, 0, -1)]
    new = [_deal(cleared + 60 * i, 2.0 if i % 3 == 0 else -1.0)
           for i in range(1, 38)]
    v, _ = _judge(sup, cfg, old + new, _cfgs(
        min_trades=80, watch_min_trades=80, quarantine_losses=11,
        quarantine_pf=0.8, watch_pf=1.0))
    assert v.state == "ok"
    assert "(30g)" in v.reason, v.reason
    assert f"karar {v.judged_trades} islem" in v.reason, v.reason
    assert f"PF {v.judged_pf:.2f}" in v.reason.split("karar", 1)[1], v.reason


def test_watch_reason_names_the_window_the_decision_used():
    """Same split as the ok case, but n after release is enough to watch.

    Decision reads watch_n / watch_pf_val (since release). Reason used to
    print only the 30-day profit_factor.
    """
    sup = _sup()
    cleared = NOW - 10 * HOUR
    cfg = SymbolConfig(symbol="NAS100")
    sup.verdicts["NAS100"] = SymbolVerdict(
        symbol="NAS100", history_cleared_at=cleared)
    old = [_deal(cleared - 600 * i, 5.0) for i in range(30, 0, -1)]
    new = [_deal(cleared + 60 * i, 1.0 if i % 2 == 0 else -1.2)
           for i in range(1, 81)]
    v, _ = _judge(sup, cfg, old + new, _cfgs(
        min_trades=80, watch_min_trades=80, quarantine_losses=11,
        quarantine_pf=0.8, watch_pf=1.0))
    assert v.state == "watch", v.reason
    assert "(30g)" in v.reason, v.reason
    assert f"karar {80} islem" in v.reason, v.reason
    assert "karar" in v.reason
    after = v.reason.split("karar", 1)[1]
    assert "PF " in after, v.reason


@pytest.mark.parametrize("losses,expected", [(3, True), (4, True), (5, False)])
def test_the_threshold_is_honoured_exactly(losses, expected):
    sup = _sup()
    applied = NOW - 2 * HOUR
    cfg = SymbolConfig(symbol="NAS100", opt_updated_at=applied)
    trades = [_deal(applied + 60 * i, -5.0) for i in range(1, 5)]  # 4 losers

    v, _ = _judge(sup, cfg, trades, _cfgs(quarantine_losses=losses))

    assert (v.state == "quarantine") is expected
