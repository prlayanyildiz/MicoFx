"""Panel/daily close_all must autopsy EXPERT closes (reap skips them)."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


def test_close_all_writes_autopsy_for_gone_tickets(monkeypatch):
    eng = Engine.__new__(Engine)
    eng._positions = [{
        "ticket": 324842945, "symbol": "XAUUSD", "side": "sell",
        "magic": 990021, "price_open": 4470.48, "sl": 4477.22,
        "tp": 0.0, "volume": 0.02, "profit": 134.08, "swap": 0.0, "time": 1,
    }]
    eng.store = SimpleNamespace(symbols={
        "XAUUSD": SimpleNamespace(magic=990021, symbol="XAUUSD"),
    })
    eng.execution = SimpleNamespace(
        snapshot=lambda ticket: {
            "symbol": "XAUUSD", "side": "sell", "entry": 4470.48,
            "original_sl": 4477.22, "risk_dist": 6.74, "mfe": 67.0,
        },
    )
    rows: list[dict] = []

    def _safe(**fields):
        rows.append(fields)

    eng._autopsy_safe = _safe  # type: ignore[method-assign]
    eng._autopsy_float = Engine._autopsy_float  # type: ignore[method-assign]
    eng._broker_now_int = lambda: 1788535900  # type: ignore[method-assign]
    eng._reload_positions = lambda: True  # type: ignore[method-assign]

    def _close_all(magics=None, symbol=None):
        eng._positions = []
        return 1, 0

    eng.client = SimpleNamespace(close_all=_close_all)
    monkeypatch.setattr(
        "micofx.engine.LOG.emit",
        lambda msg, level="INFO", symbol="": None,
    )

    closed, remaining = eng.close_all(reason="panel tumunu kapat")
    assert closed == 1 and remaining == 0
    assert len(rows) == 1
    assert rows[0]["ticket"] == 324842945
    assert rows[0]["comment"] == "panel tumunu kapat"
    assert rows[0]["profit"] == pytest.approx(134.08)
