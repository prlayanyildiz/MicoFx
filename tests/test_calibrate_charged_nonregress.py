"""Spread calibrate must not widen when charged holdout would regress (NAS100)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer
from micofx.spread_calibration import Calibration


@pytest.fixture(autouse=True)
def _unfreeze_calibrate(monkeypatch):
    monkeypatch.setattr(
        "scripts.exec_gates.pipeline_frozen", lambda: False)


def test_recalibrate_skips_when_pipeline_frozen(monkeypatch):
    monkeypatch.setattr(
        "scripts.exec_gates.pipeline_frozen", lambda: True)
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
    opt._holdout_costed = MagicMock()
    opt._recalibrate_spread_cap("NAS100", "M30")
    store.update_symbol.assert_not_called()
    client.bars.assert_not_called()


def test_recalibrate_refuses_charged_regressive_widen(monkeypatch):
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

    fake = Calibration(
        symbol="NAS100", timeframe="M30", bands=[],
        cap=0.06, reason="band",
    )
    monkeypatch.setattr(
        "micofx.optimizer.calibrate",
        lambda *a, **k: fake,
    )

    def fake_holdout(symbol, timeframe, strategy, params, **kw):
        msa = float(params.get("max_spread_atr", cfg.max_spread_atr) or 0)
        # Live 0.05 stamps better than calibrate's 0.06 (Claude/Cursor NAS).
        if abs(msa - 0.05) < 1e-9:
            return {"net_r": 103.5, "profit_factor": 1.35}
        return {"net_r": 91.6, "profit_factor": 1.33}

    opt._holdout_costed = fake_holdout  # type: ignore[method-assign]
    monkeypatch.setattr(
        "scripts.exec_gates.charged_slice_nets",
        lambda row, field=None, value=None, **kw: [10.0] * 6,
    )
    opt._recalibrate_spread_cap("NAS100", "M30")
    store.update_symbol.assert_not_called()
    assert cfg.max_spread_atr == 0.05


def test_recalibrate_allows_charged_improving_widen(monkeypatch):
    cfg = SimpleNamespace(
        symbol="US30", strategy="channel_break", timeframe="M30",
        max_spread_atr=0.08, opt_summary={},
    )
    store = SimpleNamespace(
        symbols={"US30": cfg},
        update_symbol=MagicMock(side_effect=lambda s, patch, source=None: (
            setattr(cfg, "max_spread_atr", patch["max_spread_atr"]), cfg)),
        opt_params=lambda: {},
    )
    client = SimpleNamespace(
        bars=MagicMock(return_value=object()),
        info=MagicMock(return_value={"point": 0.01}),
    )
    opt = Optimizer.__new__(Optimizer)
    opt.store = store
    opt.client = client
    monkeypatch.setattr(
        "micofx.optimizer.calibrate",
        lambda *a, **k: Calibration(
            symbol="US30", timeframe="M30", bands=[],
            cap=0.12, reason="band"),
    )

    def fake_holdout(symbol, timeframe, strategy, params, **kw):
        msa = float(params.get("max_spread_atr", cfg.max_spread_atr) or 0)
        if abs(msa - 0.08) < 1e-9:
            return {"net_r": 25.0, "profit_factor": 1.20}
        return {"net_r": 29.4, "profit_factor": 1.23}

    opt._holdout_costed = fake_holdout  # type: ignore[method-assign]
    monkeypatch.setattr(
        "scripts.exec_gates.charged_slice_nets",
        lambda row, field=None, value=None, **kw: (
            [5.0, 5.0, 5.0, 5.0, 5.0, 5.0]
            if value is None else [6.0, 6.0, 6.0, 6.0, 6.0, 6.0]
        ),
    )
    opt._recalibrate_spread_cap("US30", "M30")
    store.update_symbol.assert_called_once()
    assert cfg.max_spread_atr == 0.12


def test_recalibrate_refuses_six_slice_erosion_widen(monkeypatch):
    """SpotBrent 04.09: last-seg charged up, 6-slice 3/6→1/6 — refuse."""
    cfg = SimpleNamespace(
        symbol="SpotBrent", strategy="mtf_pullback", timeframe="M30",
        max_spread_atr=0.05, opt_summary={},
        to_dict=lambda: {
            "symbol": "SpotBrent", "timeframe": "M30",
            "strategy": "mtf_pullback", "max_spread_atr": 0.05,
            "use_sessions": True,
            "sessions": [{"start": "14:00", "end": "22:00"}],
        },
    )
    store = SimpleNamespace(
        symbols={"SpotBrent": cfg},
        update_symbol=MagicMock(return_value=cfg),
        opt_params=lambda: {},
        system=SimpleNamespace(charge_costs=True),
    )
    client = SimpleNamespace(
        bars=MagicMock(return_value=object()),
        info=MagicMock(return_value={"point": 0.01}),
    )
    opt = Optimizer.__new__(Optimizer)
    opt.store = store
    opt.client = client
    monkeypatch.setattr(
        "micofx.optimizer.calibrate",
        lambda *a, **k: Calibration(
            symbol="SpotBrent", timeframe="M30", bands=[],
            cap=0.08, reason="band"),
    )

    def fake_holdout(symbol, timeframe, strategy, params, **kw):
        # Last-segment illusion: widen looks better.
        msa = float(params.get("max_spread_atr", cfg.max_spread_atr) or 0)
        if abs(msa - 0.05) < 1e-9:
            return {"net_r": 40.0}
        return {"net_r": 80.0}

    opt._holdout_costed = fake_holdout  # type: ignore[method-assign]

    def fake_slices(row, field=None, value=None, **kw):
        if value is None or abs(float(value) - 0.05) < 1e-9:
            return [0.0, -1.9, 11.7, 5.1, -6.6, 41.5]  # 3/6
        return [0.0, -8.3, -25.1, -3.8, -27.8, 81.0]  # 1/6

    monkeypatch.setattr(
        "scripts.exec_gates.charged_slice_nets", fake_slices)
    opt._recalibrate_spread_cap("SpotBrent", "M30")
    store.update_symbol.assert_not_called()
    assert cfg.max_spread_atr == 0.05
