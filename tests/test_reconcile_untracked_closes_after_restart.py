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
            "ticket": 98, "position": 324655544, "symbol": "XAUUSD",
            "magic": 990021, "volume": 0.01, "price": 4478.42,
            "profit": 0.0, "commission": -0.05, "swap": 0.0,
            "time": 999_900, "comment": "", "reason": 0,
            "entry": 0, "type": 0,  # DEAL_ENTRY_IN / BUY
        },
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
    row = next(r for r in eng._trade_autopsies if int(r.get("ticket") or 0) == 324655544)
    assert row.get("side") == "buy"
    assert abs(float(row.get("entry") or 0) - 4478.42) < 1e-6
    assert abs(float(row.get("r_realised") or 0) + 1.0) < 1e-3
    assert eng._untracked_closes_done is True
    # Second call is a no-op
    eng._reconcile_untracked_closes()
    assert eng.client.deals_since.call_count == 1


def test_reconcile_enriches_thin_autopsy_already_logged():
    """First ship logged TRADE without IN book; next restart fills R."""
    eng = Engine.__new__(Engine)
    eng.client = MagicMock()
    eng.client.connected = True
    eng.client.broker_now.return_value = 1_000_000.0
    eng.client.deals_since.return_value = [
        {
            "ticket": 98, "position": 324655544, "symbol": "XAUUSD",
            "magic": 990021, "volume": 0.01, "price": 4478.42,
            "profit": 0.0, "commission": -0.05, "swap": 0.0,
            "time": 999_900, "comment": "", "reason": 0,
            "entry": 0, "type": 0,
        },
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
    }
    eng.store.system = SystemConfig()
    eng._positions = []
    thin = {
        "symbol": "XAUUSD", "ticket": 324655544, "side": "", "entry": None,
        "r_realised": None, "profit": -3.49, "exit_reason": "sl",
    }
    eng._trade_autopsies = [thin]
    eng._trade_autopsy_limit = 100
    eng._trade_autopsies_dirty = False
    eng._untracked_closes_done = False
    eng.execution = MagicMock()
    eng._rebuild_autopsy_pending = lambda: None
    eng._pending_autopsy_add = lambda row: None

    eng._reconcile_untracked_closes()

    assert len(eng._trade_autopsies) == 1
    assert thin.get("side") == "buy"
    assert abs(float(thin.get("entry") or 0) - 4478.42) < 1e-6
    assert abs(float(thin.get("r_realised") or 0) + 1.0) < 1e-3
    assert eng._trade_autopsies_dirty is True


def test_reconcile_thin_lookback_survives_long_open_btc():
    """If BTC keeps the book open past 2h, thin XAU deals must still load."""
    eng = Engine.__new__(Engine)
    eng.client = MagicMock()
    eng.client.connected = True
    # 6h after the thin exit — default 2h window would miss IN/OUT.
    eng.client.broker_now.return_value = 999_990 + 6 * 3600
    eng.client.deals_since.return_value = [
        {
            "ticket": 98, "position": 324655544, "symbol": "XAUUSD",
            "magic": 990021, "volume": 0.01, "price": 4478.42,
            "profit": 0.0, "commission": -0.05, "swap": 0.0,
            "time": 999_900, "comment": "", "reason": 0,
            "entry": 0, "type": 0,
        },
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
    }
    eng.store.system = SystemConfig()
    eng._positions = []
    thin = {
        "symbol": "XAUUSD", "ticket": 324655544, "side": "", "entry": None,
        "r_realised": None, "profit": -3.54, "exit_reason": "sl",
        "exit_time": 999_990,
    }
    eng._trade_autopsies = [thin]
    eng._trade_autopsy_limit = 100
    eng._trade_autopsies_dirty = False
    eng._untracked_closes_done = False
    eng.execution = MagicMock()
    eng._rebuild_autopsy_pending = lambda: None
    eng._pending_autopsy_add = lambda row: None

    eng._reconcile_untracked_closes()

    since = eng.client.deals_since.call_args[0][0]
    assert since <= 999_990 - 86400.0 + 1.0
    assert thin.get("side") == "buy"
    assert abs(float(thin.get("r_realised") or 0) + 1.0) < 1e-3
