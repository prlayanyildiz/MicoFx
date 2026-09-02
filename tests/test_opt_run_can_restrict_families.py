"""A manual search must be able to name the families it wants.

store.opt_params() always re-appends every shipped family, so saving a
subset cannot actually restrict a sweep. The 26.08 channel_break holdout had
to run that family only - without applying, without leaving auto-reopt
stuck on a subset. The start() door already does this for timeframes;
families need the same one-off override.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, symbols):
        self.symbols = {c.symbol: c for c in symbols}
        self.settings: dict = {}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value

    def opt_params(self):
        return {}


def _opt(symbols) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._lock = threading.RLock()
    opt.store = _Store(symbols)
    opt.job = {}
    opt._cancel = threading.Event()
    opt._force_apply = False
    opt._thread = None
    opt._run = lambda *a, **k: None
    return opt


def _cfg(symbol):
    return SymbolConfig(symbol=symbol, magic=abs(hash(symbol)) % 10_000)


BOOK = [_cfg("GER40"), _cfg("NAS100")]

NEW = ["channel_break"]


class _FakeThread:
    """Capture the worker args without running MT5."""

    def __init__(self, target=None, args=(), kwargs=None, name="", daemon=False):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.name = name
        self.daemon = daemon

    def start(self):
        return None

    def is_alive(self):
        return False


def test_a_named_family_subset_lands_on_the_job():
    opt = _opt(BOOK)
    res = opt.start(strategies=NEW, apply_best=False)
    assert res["ok"] is True
    assert res["job"]["strategies"] == NEW
    assert res["job"]["apply_best"] is False


def test_the_worker_is_handed_the_family_subset(monkeypatch):
    monkeypatch.setattr("micofx.optimizer.threading.Thread", _FakeThread)
    opt = _opt(BOOK)
    opt.start(strategies=NEW, apply_best=False, force=True)
    assert opt._thread.args[4] == NEW


def test_unknown_family_names_are_dropped_and_an_empty_kept_set_is_refused():
    res = _opt(BOOK).start(strategies=["not_a_family"])
    assert res["ok"] is False
    assert "strateji" in res["error"].lower() or "aile" in res["error"].lower()
    assert "not_a_family" in res["error"]


def test_a_mix_keeps_only_the_searchable_names():
    opt = _opt(BOOK)
    res = opt.start(strategies=["not_a_family", "channel_break", "stoch_flip"])
    assert res["ok"] is True
    assert res["job"]["strategies"] == ["channel_break"]


def test_omitting_strategies_still_inherits_saved_params():
    """None/empty is the old door - scheduled reopt must not shrink."""
    opt = _opt(BOOK)
    res = opt.start(apply_best=True)
    assert res["ok"] is True
    assert res["job"]["strategies"] == []


def test_last_opt_job_records_the_family_subset():
    opt = _opt(BOOK)
    opt.start(strategies=NEW, apply_best=False, force=False)
    job = opt.store.settings.get("last_opt_job") or {}
    assert job.get("strategies") == NEW
    assert job.get("apply_best") is False
