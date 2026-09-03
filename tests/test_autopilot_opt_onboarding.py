"""Autopilot opt onboarding: never-searched → WFO; stamped + hold floor → enable."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import (
    ENABLE_MIN_HOLD_NET_R,
    AutoPilot,
    mark_operator_disabled,
)
from micofx.models import SymbolConfig


class _Opt:
    busy = False
    calls: list

    def __init__(self) -> None:
        self.calls = []

    def start(self, symbols, apply_best=True, source="manual", **_):
        self.calls.append({"symbols": list(symbols), "apply_best": apply_best,
                           "source": source})
        return {"ok": True, "job": {}}


def _cfg(name: str, *, enabled=False, stamped=False, net_r=30.0, pr=0.75):
    c = SymbolConfig(symbol=name, magic=abs(hash(name)) % 9000 + 100, enabled=enabled)
    if stamped:
        c.opt_updated_at = 1_700_000_000.0
        c.opt_summary = {
            "holdout": {"net_r": net_r, "trades": 40, "expectancy": net_r / 40},
            "positive_ratio": pr,
            "validated": True,
        }
    return c


def _ap(symbols: list[SymbolConfig], opt=None) -> AutoPilot:
    settings: dict = {}

    def _update(sym, patch, source=""):
        row = store.symbols[sym]
        for k, v in patch.items():
            setattr(row, k, v)
        return row

    store = SimpleNamespace(
        system=SimpleNamespace(autopilot_enabled=True, autopilot_interval_sec=900,
                               charge_costs=False, autostart_bot=True,
                               kasa_auto_enabled=True),
        symbols={c.symbol: c for c in symbols},
        get_setting=lambda k, d=None: settings.get(k, d),
        set_setting=lambda k, v: settings.__setitem__(k, v),
        update_system=lambda *_a, **_k: None,
        update_symbol=_update,
    )
    eng = SimpleNamespace(
        store=store,
        client=SimpleNamespace(connected=True),
        supervisor=SimpleNamespace(optimizer=opt or _Opt(), settings={}),
        entry_blocks=lambda: {"since": 1.0, "rows": []},
        _positions=[],
    )
    return AutoPilot(eng)


def test_queues_one_never_searched_symbol_per_tick():
    opt = _Opt()
    ap = _ap([_cfg("NEW1"), _cfg("NEW2"), _cfg("OLD", stamped=True)], opt=opt)
    notes = ap._apply_opt_lifecycle()
    assert opt.calls and opt.calls[0]["symbols"] == ["NEW1"]
    assert opt.calls[0]["source"] == "onboarding"
    assert any("NEW1" in n for n in notes)


def test_skips_queue_when_opt_busy():
    opt = _Opt()
    opt.busy = True
    ap = _ap([_cfg("NEW1")], opt=opt)
    assert ap._lifecycle_queue_onboarding() == []
    assert not opt.calls


def test_enables_stamped_newcomer_above_hold_floor():
    ap = _ap([_cfg("READY", stamped=True, net_r=ENABLE_MIN_HOLD_NET_R + 1)])
    notes = ap._lifecycle_enable()
    assert ap.store.symbols["READY"].enabled is True
    assert any("READY" in n and "acildi" in n for n in notes)


def test_does_not_enable_below_hold_floor():
    ap = _ap([_cfg("WEAK", stamped=True, net_r=ENABLE_MIN_HOLD_NET_R - 1)])
    assert ap._lifecycle_enable() == []
    assert ap.store.symbols["WEAK"].enabled is False


def test_operator_disable_blocks_reenable():
    cfg = _cfg("SPOT", stamped=True, net_r=50.0)
    ap = _ap([cfg])
    mark_operator_disabled(ap.store, "SPOT", disabled=True)
    assert ap._lifecycle_enable() == []
    assert ap.store.symbols["SPOT"].enabled is False


def test_never_stamped_closed_symbol_applies_config():
    """First stamp on a closed name must write opt_updated_at (onboarding path)."""
    from micofx.optimizer import Optimizer

    class Store:
        def __init__(self, cfg):
            self.symbols = {cfg.symbol: cfg}
            self.runs = []

        def opt_params(self):
            return {}

        def get_setting(self, key, default=None):
            return default

        def record_opt_run(self, symbol, score, payload, applied):
            self.runs.append({"applied": applied, "payload": payload})
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

    slice_ok = {
        "trades": 80, "wins": 40, "losses": 40, "win_rate": 50.0,
        "net_r": 25.0, "expectancy": 0.3, "profit_factor": 1.5,
        "max_dd_r": 4.0, "score": 8.0, "cost_per_trade_r": 0.04,
    }
    cfg = SymbolConfig(symbol="NEWFX", magic=1, strategy="burst",
                       timeframe="M30", sl_atr_mult=1.0, enabled=False)
    cfg.opt_updated_at = 0.0
    store = Store(cfg)
    opt = Optimizer(store=store, client=Client())
    opt._force_apply = True
    opt._recalibrate_spread_cap = lambda *a, **k: None
    opt.job = {"source": "onboarding"}
    plan = {
        "cfg": cfg,
        "started": 0.0,
        "attempts": [{
            "ok": True, "validated": True, "order": 0,
            "timeframe": "M30", "strategy": "burst",
            "charge_costs": False, "holdout_days": 30.0,
            "best": {
                "score": 9.0,
                "params": {"sl_atr_mult": 2.0},
                "selection": dict(slice_ok),
                "validation": dict(slice_ok),
                "holdout": dict(slice_ok),
                "positive_ratio": 0.8,
            },
        }],
    }
    report = opt._finish_symbol(plan, apply_best=True)
    assert report.get("applied") is True, report
    assert report.get("closed_stamped") is True
    assert store.symbols["NEWFX"].enabled is False
    assert store.symbols["NEWFX"].sl_atr_mult == 2.0
    assert float(store.symbols["NEWFX"].opt_updated_at) > 0
