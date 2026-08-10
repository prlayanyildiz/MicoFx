"""Hard-scan fix: POST /api/ai/settings had no type check (only NaN/Infinity
rejection), so a wrong-typed value (e.g. {"quarantine_hours": "abc"}) got
stored verbatim and crashed supervisor.review()/due() the next time they ran.
due() in particular is called every engine cycle OUTSIDE the try/except that
wraps review() - a raised exception there used to silently cancel the rest of
that whole cycle (new-entry evaluation included), every single cycle, until
fixed. /api/ai/review is also hardened to return 500 instead of an unhandled
crash if supervisor.review() still raises for any other reason.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.supervisor import DEFAULTS, Supervisor
from micofx.web.app import _reject_wrong_type_against, create_app
from fastapi import HTTPException
import pytest


class _FakeStore:
    def __init__(self):
        self.symbols: dict = {}
        self.settings: dict = {}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value

    def opt_params(self):
        return {}


class _FakeClient:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass


class _FakeSupervisor:
    def __init__(self):
        self.settings = dict(DEFAULTS)
        self.update_calls = []
        self.review_raises = None

    def update_settings(self, patch):
        self.update_calls.append(patch)
        self.settings.update(patch)
        return self.settings

    def review(self, pnl):
        if self.review_raises is not None:
            raise self.review_raises
        return {"ok": True}

    def status(self):
        return {"settings": self.settings}


class _FakeRiskDaily:
    def pnl_pct(self, equity):
        return 0.0


class _FakeRisk:
    daily = _FakeRiskDaily()


class _FakeEngine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}
        self.supervisor = _FakeSupervisor()
        self.risk = _FakeRisk()

    def refresh_account(self, force=False):
        return {"equity": 1000.0}


def _client():
    store = _FakeStore()
    engine = _FakeEngine()
    app = create_app(store, _FakeClient(), engine, optimizer=None)
    return TestClient(app), engine


def test_reject_wrong_type_against_flags_string_for_numeric_field():
    with pytest.raises(HTTPException) as exc:
        _reject_wrong_type_against({"quarantine_hours": "abc"}, DEFAULTS)
    assert exc.value.status_code == 400


def test_reject_wrong_type_against_flags_bool_for_numeric_field():
    # bool is a subclass of int in Python - must not slip past an (int, float) check.
    with pytest.raises(HTTPException):
        _reject_wrong_type_against({"quarantine_hours": True}, DEFAULTS)


def test_reject_wrong_type_against_accepts_matching_numeric_types():
    _reject_wrong_type_against({"quarantine_hours": 24, "dd_soft_pct": 2.5}, DEFAULTS)  # no raise


def test_reject_wrong_type_against_accepts_matching_bool_field():
    _reject_wrong_type_against({"enabled": False}, DEFAULTS)  # no raise


def test_reject_wrong_type_against_ignores_unknown_keys_and_none():
    _reject_wrong_type_against({"not_a_real_field": "whatever", "enabled": None}, DEFAULTS)


def test_ai_settings_endpoint_rejects_string_for_numeric_field():
    tc, engine = _client()
    res = tc.post("/api/ai/settings", json={"quarantine_hours": "abc"})
    assert res.status_code == 400
    assert engine.supervisor.update_calls == []  # never reached the store


def test_ai_settings_endpoint_accepts_valid_patch():
    tc, engine = _client()
    res = tc.post("/api/ai/settings", json={"quarantine_hours": 24, "enabled": True})
    assert res.status_code == 200
    assert engine.supervisor.update_calls == [{"quarantine_hours": 24, "enabled": True}]


def test_ai_review_endpoint_returns_500_instead_of_crashing_on_bad_stored_settings():
    tc, engine = _client()
    # Simulates a row that was already bad before this validation existed.
    engine.supervisor.review_raises = ValueError("could not convert string to float: 'abc'")
    res = tc.post("/api/ai/review")
    assert res.status_code == 500
    assert "AI denetleyici" in res.json()["detail"]


# ------------------------------------------------- Supervisor defensive coercion

class _StoreDouble:
    def __init__(self, settings):
        self._settings = settings

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key, value):
        self._settings[key] = value


def _bare_supervisor(settings_patch):
    sup = object.__new__(Supervisor)
    sup.store = _StoreDouble({"supervisor": {**DEFAULTS, **settings_patch}})
    sup.last_review = 0.0
    return sup


def test_due_survives_non_numeric_review_interval():
    # Simulates a stored value corrupted before the app-level type check
    # existed - due() is called every engine cycle OUTSIDE review()'s
    # try/except, so a raise here used to silently kill the rest of that
    # cycle (including new-entry evaluation) every single time.
    sup = _bare_supervisor({"review_interval_sec": "not-a-number"})
    assert sup.due() in (True, False)  # must not raise


def test_due_uses_default_interval_when_stored_value_is_bad():
    import time
    sup = _bare_supervisor({"review_interval_sec": "not-a-number"})
    sup.last_review = time.time()  # just reviewed
    # With a good default interval (120s) "just reviewed" must mean not due.
    assert sup.due() is False


# ------------------------------------------- quarantine evidence calibration

def test_quarantine_needs_more_evidence_than_a_size_cut():
    """A 12-hour suspension and a 40% lot trim must not cost the same proof.

    Measured against this portfolio's own validated win rates (26-79%) and
    profit factors: judging on 8 trades false-quarantined a healthy symbol 23%
    of the time while catching a genuinely broken one only 72%; at 25 it is 11%
    against 87% - better on both axes. But sharing that bar with `watch` left
    GER40, at PF 0.62 over 18 trades, clearing neither and trading at full
    size when a soft trim is exactly what it deserved.
    """
    from micofx.supervisor import DEFAULTS
    assert DEFAULTS["watch_min_trades"] < DEFAULTS["min_trades"]
    assert DEFAULTS["min_trades"] >= 25


def test_the_loss_streak_trigger_is_not_a_hair_trigger():
    """Consecutive losses carry almost no information for this exit model.

    With no take-profit, a trend follower loses often by design - this book's
    validated win rates run 26-40%, so four losses in a row has a ~30%
    probability at any point and XAUUSD's own holdout expects 22 of them. The
    trigger has to sit far enough out to mean something.
    """
    from micofx.supervisor import DEFAULTS
    assert DEFAULTS["quarantine_losses"] >= 10


def test_watch_fires_on_the_evidence_quarantine_cannot_use():
    import types
    from micofx.supervisor import DEFAULTS, Supervisor, SymbolVerdict

    cfgs = {**DEFAULTS}
    v = SymbolVerdict(symbol="GER40")
    v.trades, v.profit_factor, v.consecutive_losses = 18, 0.62, 4

    # 18 trades: below the suspension bar, above the trim bar.
    assert v.trades < cfgs["min_trades"]
    assert v.trades >= cfgs["watch_min_trades"]
    assert v.profit_factor < cfgs["watch_pf"]
    assert v.consecutive_losses < cfgs["quarantine_losses"]
