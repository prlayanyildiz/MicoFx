"""``max_spread_atr`` goes stale the moment the timeframe moves.

It is a ratio against ATR, so the same spread divides down as the bars get
bigger: 0.12 cut 1.5% of FRA40's M30 bars and 57.9% of its M5 bars. On 14.08 an
apply moved four symbols' timeframes and every cap beside them silently stopped
meaning what it had meant - nothing was written, nothing was logged, and the
book's fill rate changed underneath.

So an apply that lands re-reads the cap off the timeframe that is now live. The
reading itself is asymmetric by design (see spread_calibration): it can widen a
gate on evidence and can never narrow one without.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


class _Bars:
    """GER40's shape: the expensive bars are also the strongly trending ones.

    That is the only shape the calibration will widen a gate on, so it is the
    one a "cap moved" test has to be built from.
    """

    def __init__(self, n=3000):
        rng = np.random.default_rng(3)
        drift = np.where(np.arange(n) % 4 == 0, 2.5, 0.05)
        step = rng.normal(drift, 0.4, n)
        self.close = 1000.0 + np.cumsum(step)
        self.open = self.close - step
        self.high = np.maximum(self.open, self.close) + 0.5
        self.low = np.minimum(self.open, self.close) - 0.5
        self.spread = np.where(np.arange(n) % 4 == 0, 40.0, 2.0).astype(float)

    def __len__(self):
        return len(self.close)


class _Cfg:
    def __init__(self, cap: float):
        self.max_spread_atr = cap


class _Client:
    def __init__(self, bars=None, info=None):
        self._bars, self._info = bars, info
        self.asked: list[tuple[str, str, int]] = []

    def bars(self, symbol, timeframe, count):
        self.asked.append((symbol, timeframe, count))
        return self._bars

    def info(self, symbol):
        return self._info


class _Store:
    def __init__(self, cap: float):
        self.symbols = {"NAS100": _Cfg(cap)}
        self.writes: list[tuple[str, dict, str]] = []

    def update_symbol(self, symbol, patch, source="bilinmeyen"):
        self.writes.append((symbol, patch, source))
        self.symbols[symbol].max_spread_atr = patch["max_spread_atr"]


def _opt(store: _Store, client: _Client) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store, opt.client = store, client
    return opt


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    from micofx.logbus import LOG
    monkeypatch.setattr(LOG, "emit", lambda *a, **k: None)


def test_the_new_timeframe_is_the_one_read():
    """Reading the old timeframe's bars would reproduce the stale cap exactly."""
    client = _Client(_Bars(), {"point": 0.01})
    _opt(_Store(0.02), client)._recalibrate_spread_cap("NAS100", "M5")
    assert client.asked, "no bars were fetched, so nothing was recalibrated"
    assert client.asked[0][1] == "M5"


def test_a_changed_cap_is_written_and_attributed():
    store = _Store(0.02)
    _opt(store, _Client(_Bars(), {"point": 0.01}))._recalibrate_spread_cap("NAS100", "M5")
    assert store.writes, "the reading never reached the symbol"
    symbol, patch, source = store.writes[0]
    assert symbol == "NAS100" and "max_spread_atr" in patch
    assert source == "spread kalibrasyonu", "the audit trail must name this door"


def test_an_unchanged_cap_writes_nothing():
    """Every apply would otherwise stamp a config change that changed nothing."""
    store = _Store(0.02)
    opt = _opt(store, _Client(_Bars(), {"point": 0.01}))
    opt._recalibrate_spread_cap("NAS100", "M5")
    store.writes.clear()
    opt._recalibrate_spread_cap("NAS100", "M5")
    assert store.writes == []


def test_missing_bars_leave_the_cap_alone():
    store = _Store(0.09)
    _opt(store, _Client(None, {"point": 0.01}))._recalibrate_spread_cap("NAS100", "M5")
    assert store.writes == []
    assert store.symbols["NAS100"].max_spread_atr == 0.09


def test_a_broken_reading_never_breaks_the_apply():
    """Losing a calibration is not a reason to lose an apply."""
    class _Boom(_Client):
        def bars(self, *a):
            raise RuntimeError("terminal gitti")

    store = _Store(0.09)
    _opt(store, _Boom())._recalibrate_spread_cap("NAS100", "M5")   # must not raise
    assert store.writes == []


def test_an_unknown_symbol_is_a_no_op():
    store = _Store(0.09)
    _opt(store, _Client(_Bars(), {"point": 0.01}))._recalibrate_spread_cap("YOKSA", "M5")
    assert store.writes == []


def test_the_apply_path_calls_it():
    """The hook has to sit on the branch where the config actually landed."""
    import inspect

    src = inspect.getsource(Optimizer)
    assert 'self._recalibrate_spread_cap(cfg.symbol, report["timeframe"])' in src
    after = src[src.index("self._recalibrate_spread_cap(cfg.symbol"):]
    assert "uygulama reddedildi" not in after[:200], (
        "a refused apply must not trigger a recalibration")


def _finish_plan(symbol="NAS100", timeframe="M5", strategy="micro_rev"):
    from micofx.models import SymbolConfig

    slice_ok = {
        "trades": 80, "wins": 40, "losses": 40, "win_rate": 50.0,
        "net_r": 20.0, "expectancy": 0.25, "profit_factor": 1.4,
        "max_dd_r": 4.0, "score": 8.0, "cost_per_trade_r": 0.04,
    }
    cfg = SymbolConfig(symbol=symbol, magic=1, strategy="t3_stoch",
                       timeframe="M15", sl_atr_mult=1.0)
    cfg.opt_updated_at = 0.0
    cfg.opt_summary = {}
    return {
        "cfg": cfg,
        "started": 0.0,
        "attempts": [{
            "ok": True, "validated": True, "order": 0,
            "timeframe": timeframe, "strategy": strategy,
            "charge_costs": False,
            "holdout_days": 30.0,
            "best": {
                "score": 9.0,
                "params": {"sl_atr_mult": 1.2},
                "selection": dict(slice_ok),
                "validation": dict(slice_ok),
                "holdout": dict(slice_ok),
                "positive_ratio": 0.8,
            },
        }],
    }


def _finish_opt(apply_ok=True):
    class Store:
        def __init__(self):
            self.symbols = {}

        def opt_params(self):
            return {}

        def get_setting(self, key, default=None):
            return default

        def record_opt_run(self, *a, **k):
            return None

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
    hooks = []
    opt._recalibrate_spread_cap = lambda symbol, timeframe: hooks.append((symbol, timeframe))
    if not apply_ok:
        opt.apply = lambda *a, **k: {"ok": False, "error": "TF kilit"}
    return opt, store, hooks


def test_a_successful_apply_recalibrates_the_timeframe_that_landed():
    opt, store, hooks = _finish_opt(apply_ok=True)
    plan = _finish_plan()
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    report = opt._finish_symbol(plan, apply_best=True)
    assert report.get("applied") is True, report
    assert hooks == [("NAS100", "M5")], hooks


def test_a_refused_apply_does_not_recalibrate():
    opt, store, hooks = _finish_opt(apply_ok=False)
    plan = _finish_plan()
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    report = opt._finish_symbol(plan, apply_best=True)
    assert report.get("applied") is False
    assert hooks == [], hooks
