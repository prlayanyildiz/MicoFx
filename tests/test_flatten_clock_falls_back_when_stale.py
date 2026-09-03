"""H2: weekend/session flatten must not die when decision_now is stale."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


def test_flatten_clock_falls_back_to_broker_now_when_decision_stale():
    store = MagicMock()
    store.system = SimpleNamespace(trade_all_hours=False, day_end_flatten_min=0)
    store.get_setting = MagicMock(return_value=None)
    store.set_setting = MagicMock()
    client = SimpleNamespace(
        connected=True,
        broker_now=lambda: 1_700_000_000.0,
        server_now=lambda: 0.0,
    )
    eng = Engine.__new__(Engine)
    eng.store = store
    eng.client = client
    eng._lock = __import__("threading").RLock()
    assert eng._flatten_clock(None) == 1_700_000_000.0
    assert eng._flatten_clock(1_700_000_100.0) == 1_700_000_100.0
