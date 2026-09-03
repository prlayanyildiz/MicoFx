"""Cost-free WFO must not auto-apply into the live book.

Claude 03.09 autopsy: paper-optimal SL mis-tuned GER40/BTC. Autopilot used to
flip charge_costs off; even after that fix, an operator cost-free sweep with
apply_best must not rewrite live exits.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


def _opt(*, charge_costs: bool) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._lock = threading.RLock()
    opt._cancel = threading.Event()
    opt._thread = None
    opt._force_apply = False
    opt.job = {"state": "idle"}
    opt.client = MagicMock()
    opt.store = MagicMock()
    opt.store.symbols = {
        "GER40": SymbolConfig(symbol="GER40", magic=1, enabled=True),
    }
    opt.store.system = SystemConfig(charge_costs=charge_costs)
    opt.store.opt_params.return_value = {}
    opt.store.get_setting = MagicMock(return_value=None)
    opt.store.set_setting = MagicMock()
    return opt


def test_cost_free_start_forces_apply_best_off(monkeypatch):
    started = {}

    def fake_thread(*, target, args, name, daemon):
        started["args"] = args
        return MagicMock()

    monkeypatch.setattr(threading, "Thread", fake_thread)
    opt = _opt(charge_costs=False)
    res = opt.start(["GER40"], apply_best=True)
    assert res["ok"] is True
    assert res["job"]["apply_best"] is False
    assert started["args"][1] is False


def test_charged_start_keeps_apply_best_on(monkeypatch):
    started = {}

    def fake_thread(*, target, args, name, daemon):
        started["args"] = args
        return MagicMock()

    monkeypatch.setattr(threading, "Thread", fake_thread)
    opt = _opt(charge_costs=True)
    res = opt.start(["GER40"], apply_best=True)
    assert res["ok"] is True
    assert res["job"]["apply_best"] is True
    assert started["args"][1] is True
