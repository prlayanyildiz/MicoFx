"""Closing a symbol must not be a death sentence for search.

Found live: JPN225 / SpotBrent / UK100 were switched off after a charged-negative
holdout. The grid then widened (the reason they were closed may no longer hold)
but ``Optimizer.start()`` with no name list skipped every disabled symbol, so
they could never be re-evaluated and never re-opened. Operator had to type all
21 names by hand.

A closed symbol stays in the scan. A winner is recorded on ``opt_runs`` so the
panel can show the candidate. ``apply_best`` must not write the live config and
must not flip ``enabled`` - opening stays an operator decision.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Thread:
    def __init__(self, alive=False):
        self._alive = alive

    def is_alive(self):
        return self._alive

    def start(self):
        pass


class _StartStore:
    def __init__(self, symbols):
        self.symbols = {c.symbol: c for c in symbols}

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}


def _start_opt(symbols) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._lock = threading.RLock()
    opt.store = _StartStore(symbols)
    opt.job = {}
    opt._cancel = threading.Event()
    opt._force_apply = False
    opt._thread = None
    opt._run = lambda *a, **k: None
    return opt


def _cfg(symbol, *, enabled=True):
    c = SymbolConfig(symbol=symbol, magic=abs(hash(symbol)) % 10_000)
    c.enabled = enabled
    return c


def test_a_full_scan_includes_a_closed_symbol_in_targets():
    """The loop: off because the last search failed, then never searched again."""
    opt = _start_opt([_cfg("GER40"), _cfg("JPN225", enabled=False)])
    res = opt.start()
    assert res["ok"] is True
    assert "JPN225" in res["job"]["symbols"]
    assert "GER40" in res["job"]["symbols"]


def _finish_plan(enabled: bool):
    slice_ok = {
        "trades": 80, "wins": 40, "losses": 40, "win_rate": 50.0,
        "net_r": 20.0, "expectancy": 0.25, "profit_factor": 1.4,
        "max_dd_r": 4.0, "score": 8.0, "cost_per_trade_r": 0.04,
    }
    stamped = {
        "holdout": {"net_r": 3.0, "score": 4.0, "trades": 40},
        "params": {"sl_atr_mult": 0.9},
    }
    cfg = SymbolConfig(symbol="JPN225", magic=1, strategy="t3_stoch",
                       timeframe="M5", sl_atr_mult=0.9, enabled=enabled)
    cfg.opt_updated_at = 1.0
    cfg.opt_summary = dict(stamped)
    return {
        "cfg": cfg,
        "started": 0.0,
        "attempts": [{
            "ok": True, "validated": True, "order": 0,
            "timeframe": "M30", "strategy": "mtf_pullback",
            "charge_costs": True,
            "holdout_days": 30.0,
            "best": {
                "score": 9.0,
                "params": {"sl_atr_mult": 2.0},
                "selection": dict(slice_ok),
                "validation": dict(slice_ok),
                "holdout": dict(slice_ok),
                "positive_ratio": 0.8,
            },
        }],
    }, stamped


def _finish_opt():
    class Store:
        def __init__(self):
            self.symbols = {}
            self.runs = []

        def opt_params(self):
            return {}

        def get_setting(self, key, default=None):
            return default

        def record_opt_run(self, symbol, score, payload, applied):
            self.runs.append({
                "symbol": symbol, "score": score,
                "payload": payload, "applied": applied,
            })
            return 1

        def update_symbol(self, symbol, patch, source=""):
            row = self.symbols[symbol]
            for k, v in patch.items():
                if v is not None:
                    setattr(row, k, v)
            return row

    class Client:
        connected = True

        def positions(self, magic=None, symbol=None):
            return []

    store = Store()
    opt = Optimizer(store=store, client=Client())
    opt._force_apply = True
    opt._recalibrate_spread_cap = lambda *a, **k: None
    return opt, store


def test_closed_symbol_records_a_run_and_does_not_apply():
    """Without the skip, apply_best writes opt_summary and the closed loop
    looks 'fixed' because a config landed while the symbol stayed off."""
    opt, store = _finish_opt()
    plan, stamped = _finish_plan(enabled=False)
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    before = dict(plan["cfg"].opt_summary)

    report = opt._finish_symbol(plan, apply_best=True)

    cfg = store.symbols["JPN225"]
    assert cfg.enabled is False
    assert cfg.opt_summary == before == stamped
    assert cfg.sl_atr_mult == 0.9
    assert report.get("applied") is False
    assert report.get("closed_candidate") is True
    assert "kapali sembol" in (report.get("keep_reason") or "").lower()
    assert store.runs, "opt_runs never got the candidate"
    run = store.runs[-1]
    assert run["symbol"] == "JPN225"
    assert run["applied"] is False
    assert "kapali sembol" in str(run["payload"].get("keep_reason", "")).lower()


def test_an_open_symbol_still_applies_the_same_winner():
    """The closed-symbol skip must not become a silent no-apply for the book."""
    opt, store = _finish_opt()
    plan, _ = _finish_plan(enabled=True)
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    report = opt._finish_symbol(plan, apply_best=True)
    assert report.get("applied") is True, report
    assert store.symbols["JPN225"].sl_atr_mult == 2.0
    assert store.runs[-1]["applied"] is True
