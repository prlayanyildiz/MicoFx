"""In-process autopilot must not calibrate while opt is busy or MT5 is down."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import AutoPilot, spread_auto_targets


class _BusyOpt:
    busy = True

    def _recalibrate_spread_cap(self, *_a, **_k):
        raise AssertionError("calibrate must not run while busy")


class _IdleOpt:
    busy = False
    calls: list[tuple[str, str]]

    def __init__(self) -> None:
        self.calls = []

    def _recalibrate_spread_cap(self, symbol: str, timeframe: str) -> None:
        self.calls.append((symbol, timeframe))


def _engine(*, connected: bool, opt, entry_rows=None, positions=None):
    cfg = SimpleNamespace(
        symbol="US30", enabled=True, timeframe="M30",
        max_spread_atr=0.05, partial_at_r=0.0,
        strategy="burst", opt_score=1.0, opt_updated_at=0.0,
        opt_summary={}, commission_per_lot=0.0,
    )
    store = SimpleNamespace(
        system=SimpleNamespace(
            autopilot_enabled=True,
            autopilot_interval_sec=900,
            charge_costs=True,
            autostart_bot=True,
            lot_multiplier=1.0,
            max_margin_usage_pct=50.0,
            max_concurrent_risk_pct=8.0,
            block_high_cost=True,
            max_cost_pct_of_risk=18.0,
        ),
        symbols={"US30": cfg},
        update_system=lambda *_a, **_k: store.system,
        update_symbol=lambda *_a, **_k: cfg,
    )
    client = SimpleNamespace(connected=connected, last_error="")
    eng = SimpleNamespace(
        store=store,
        client=client,
        supervisor=SimpleNamespace(
            optimizer=opt,
            update_settings=lambda patch: patch,
            status=lambda: {"verdicts": {}},
        ),
        entry_blocks=lambda: {
            "since": 1.0,
            "rows": entry_rows or [],
        },
        _positions=positions or [],
        _account={"equity": 1000.0, "leverage": 500},
        _capacity_cache={
            "margin_usage_pct": 10.0,
            "max_margin_usage_pct": 50.0,
            "global_free_slots": 2,
            "rows": [{"enabled": True, "lot": 0.1}],
        },
    )
    return AutoPilot(eng), cfg


def test_tick_skips_spread_when_optimizer_busy():
    ap, _ = _engine(connected=True, opt=_BusyOpt(), entry_rows=[{
        "symbol": "US30", "leg": "buy", "signals": 20, "opened": 1,
        "fill_rate": 0.05,
        "blocks": {"spread": 15},
    }])
    out = ap.tick()
    assert any("opt" in x.lower() or "busy" in x.lower() or "calisiyor" in x.lower()
               for x in out)


def test_tick_skips_spread_when_mt5_down():
    opt = _IdleOpt()
    ap, _ = _engine(connected=False, opt=opt, entry_rows=[{
        "symbol": "US30", "leg": "buy", "signals": 20, "opened": 1,
        "fill_rate": 0.05,
        "blocks": {"spread": 15},
    }])
    out = ap.tick()
    assert opt.calls == []
    assert any("mt5" in x.lower() or "bagli" in x.lower() for x in out)


def test_spread_auto_targets_helper_needs_evidence():
    rows = [{
        "symbol": "US30", "signals": 20, "opened": 2, "fill_rate": 0.1,
        "blocks": {"spread": 12},
    }]
    assert spread_auto_targets(rows, set(), {"US30"}) == ["US30"]
    assert spread_auto_targets(rows, {"US30"}, {"US30"}) == []
