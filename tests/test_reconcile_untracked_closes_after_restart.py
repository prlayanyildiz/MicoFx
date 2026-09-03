"""Restart must log broker closes that happened while the process was down.

XAU #324655544 hit SL during a 01:24 restart window: new PID re-adopted only
BTC, balance dropped, no TRADE/otopsi line. execution._open is empty after
restart so track()/reap never see the gone ticket — scan recent OUT deals.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import execution
from micofx.engine import Engine
from micofx.models import SymbolConfig, SystemConfig


def test_reconcile_logs_sl_close_missing_from_open_book():
    eng = Engine.__new__(Engine)
    eng.client = MagicMock()
    eng.client.connected = True
    eng.client.broker_now.return_value = 1_000_000.0
    eng.client.deals_since.return_value = [
        {
            "ticket": 99, "position": 324655544, "symbol": "XAUUSD",
            "magic": 990021, "volume": 0.01, "price": 4474.98,
            "profit": -3.44, "commission": 0.0, "swap": 0.0,
            "time": 999_990, "comment": "", "reason": execution.DEAL_REASON_SL,
            "entry": 1, "type": 1,
        },
    ]
    eng.store = MagicMock()
    eng.store.symbols = {
        "XAUUSD": SymbolConfig(symbol="XAUUSD", magic=990021, enabled=True),
        "BTCUSD": SymbolConfig(symbol="BTCUSD", magic=990116, enabled=True),
    }
    eng.store.system = SystemConfig()
    eng._positions = [
        {"ticket": 324468226, "magic": 990116, "symbol": "BTCUSD"},
    ]
    eng._trade_autopsies = []
    eng._trade_autopsy_limit = 100
    eng._trade_autopsies_dirty = False
    eng._untracked_closes_done = False
    eng.execution = MagicMock()
    eng._rebuild_autopsy_pending = lambda: None
    eng._pending_autopsy_add = lambda row: None

    logs: list[tuple[str, str]] = []
    from micofx import engine as eng_mod
    orig = eng_mod.LOG.emit

    def _capture(msg, level="INFO", symbol=None):
        logs.append((str(msg), str(level)))

    eng_mod.LOG.emit = _capture
    try:
        eng._reconcile_untracked_closes()
    finally:
        eng_mod.LOG.emit = orig

    assert any("324655544" in m and "TRADE" == lv for m, lv in logs), logs
    tickets = [int(r.get("ticket") or 0) for r in eng._trade_autopsies]
    assert 324655544 in tickets
    assert eng._untracked_closes_done is True
    # Second call is a no-op
    eng._reconcile_untracked_closes()
    assert eng.client.deals_since.call_count == 1
