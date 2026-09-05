"""Exec pipeline FREEZE — all widen/tune doors must no-op (Claude EK22-B)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_recalibrate_root_freeze():
    from micofx.optimizer import Optimizer

    cfg = SimpleNamespace(
        symbol="NAS100", strategy="burst", timeframe="M30",
        max_spread_atr=0.05, opt_summary={},
    )
    store = SimpleNamespace(
        symbols={"NAS100": cfg},
        update_symbol=MagicMock(return_value=cfg),
        opt_params=lambda: {},
    )
    client = SimpleNamespace(
        bars=MagicMock(return_value=object()),
        info=MagicMock(return_value={"point": 0.01}),
    )
    opt = Optimizer.__new__(Optimizer)
    opt.store = store
    opt.client = client
    with patch("scripts.exec_gates.pipeline_frozen", return_value=True):
        opt._recalibrate_spread_cap("NAS100", "M30")
    store.update_symbol.assert_not_called()
    client.bars.assert_not_called()


def test_spread_exec_and_income_and_trust_freeze():
    from scripts import income_dev_loop as loop
    from scripts.spread_exec import apply_spread_widen

    with patch("scripts.exec_gates.pipeline_frozen", return_value=True):
        ok, msg = apply_spread_widen(
            {}, panel="http://127.0.0.1:8900", symbol="US30",
            current_cap=0.08, history=[])
        assert ok and "FREEZE" in msg
        out = loop.apply_spread_calibration({
            "live": {"opt_busy": False, "mt5_connected": True},
            "spread_auto": ["US30"],
            "ranked": [{"symbol": "US30", "max_spread_atr": 0.08}],
            "active_symbols": ["US30"],
        })
        assert out and "FREEZE" in out[0]

    posts: list[str] = []
    with patch("scripts.income_dev_loop._api_session",
               return_value=({"Origin": "x"}, True)):
        with patch("scripts.income_dev_loop._api_post",
                   side_effect=lambda path, *a, **k: (
                       posts.append(path), (True, "{}"))[1]):
            with patch("scripts.income_dev_loop._api_get",
                       return_value={"system": {"charge_costs": True}}):
                loop.apply_trust_entries({
                    "live": {"open_symbols": []},
                    "active_symbols": ["US30"],
                })
    assert all("/spread-calibrate" not in p for p in posts)


def test_gate_pick_frozen_returns_none():
    from scripts.exec_gates import gate_pick

    with patch("scripts.exec_gates.pipeline_frozen", return_value=True):
        assert gate_pick(
            {"symbol": "X"}, {"max_spread_atr": 0.12},
            field="max_spread_atr", value_key="max_spread_atr",
        ) is None
