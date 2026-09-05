"""Autopilot must calibrate only evidence spread targets, not every flat name."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import AutoPilot


class _Opt:
    busy = False

    def __init__(self) -> None:
        self.calls: list[str] = []

    def _recalibrate_spread_cap(self, symbol: str, timeframe: str) -> None:
        self.calls.append(symbol)


def test_spread_calibrate_only_evidence_targets(monkeypatch):
    monkeypatch.setattr(
        "scripts.exec_gates.pipeline_frozen", lambda: False)
    us30 = SimpleNamespace(
        symbol="US30", enabled=True, timeframe="M30",
        max_spread_atr=0.05, partial_at_r=0.0,
        strategy="burst", opt_score=1.0, opt_updated_at=0.0,
        opt_summary={}, commission_per_lot=0.0,
    )
    ger = SimpleNamespace(
        symbol="GER40", enabled=True, timeframe="M30",
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
        symbols={"US30": us30, "GER40": ger},
        update_system=lambda *_a, **_k: store.system,
        update_symbol=lambda *_a, **_k: None,
    )
    opt = _Opt()
    eng = SimpleNamespace(
        store=store,
        client=SimpleNamespace(connected=True),
        supervisor=SimpleNamespace(
            optimizer=opt,
            update_settings=lambda patch: patch,
            status=lambda: {"verdicts": {}},
            settings={},
        ),
        entry_blocks=lambda: {
            "since": time.time(),
            "rows": [
                {"symbol": "US30", "leg": "buy", "signals": 30, "opened": 2,
                 "fill_rate": 0.06, "blocks": {"spread": 20}},
                {"symbol": "GER40", "leg": "buy", "signals": 30, "opened": 25,
                 "fill_rate": 0.83, "blocks": {"spread": 1}},
            ],
        },
        _positions=[],
        _account={"equity": 1000.0, "leverage": 500},
        _capacity_cache={
            "margin_usage_pct": 5.0,
            "max_margin_usage_pct": 50.0,
            "global_free_slots": 2,
            "rows": [{"enabled": True, "lot": 0.1}, {"enabled": True, "lot": 0.1}],
        },
    )
    ap = AutoPilot(eng)
    ap.tick()
    assert opt.calls == ["US30"]


def test_spread_calibrate_skips_when_pipeline_frozen(monkeypatch):
    """Exec freeze must block AP band-calibrate (live MSA widen path)."""
    monkeypatch.setattr(
        "scripts.exec_gates.pipeline_frozen", lambda: True)
    us30 = SimpleNamespace(
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
        symbols={"US30": us30},
        update_system=lambda *_a, **_k: store.system,
        update_symbol=lambda *_a, **_k: None,
    )
    opt = _Opt()
    eng = SimpleNamespace(
        store=store,
        client=SimpleNamespace(connected=True),
        supervisor=SimpleNamespace(
            optimizer=opt,
            update_settings=lambda patch: patch,
            status=lambda: {"verdicts": {}},
            settings={},
        ),
        entry_blocks=lambda: {
            "since": time.time(),
            "rows": [
                {"symbol": "US30", "leg": "buy", "signals": 30, "opened": 2,
                 "fill_rate": 0.06, "blocks": {"spread": 20}},
            ],
        },
        _positions=[],
        _account={"equity": 1000.0, "leverage": 500},
        _capacity_cache={
            "margin_usage_pct": 5.0,
            "max_margin_usage_pct": 50.0,
            "global_free_slots": 2,
            "rows": [{"enabled": True, "lot": 0.1}],
        },
    )
    ap = AutoPilot(eng)
    out = ap._apply_spread()
    assert out and "FREEZE" in out[0]
    assert opt.calls == []
