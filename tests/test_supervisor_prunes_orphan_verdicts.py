"""Supervisor must not keep verdicts for symbols that left the book."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.supervisor import Supervisor, SymbolVerdict


def _sup(symbols: dict) -> Supervisor:
    store = MagicMock()
    store.get_setting.return_value = {}
    store.symbols = symbols
    store.ai = MagicMock(enabled=True)
    return Supervisor(store, MagicMock())


def test_prune_orphans_drops_foreign_verdicts():
    sup = _sup({"NAS100": object(), "GER40": object()})
    with sup._lock:
        for name in ("NAS100", "FRA40", "PLTR.US-24", "UK100"):
            sup.verdicts[name] = SymbolVerdict(symbol=name)
    dropped = sup.prune_orphans()
    assert set(dropped) == {"FRA40", "PLTR.US-24", "UK100"}
    # Live GER40 with no verdict stays absent; prune does not invent rows.
    assert set(sup.verdicts) == {"NAS100"}


def test_prune_orphans_is_noop_when_aligned():
    sup = _sup({"XAUUSD": object()})
    with sup._lock:
        sup.verdicts["XAUUSD"] = SymbolVerdict(symbol="XAUUSD")
    assert sup.prune_orphans() == []
    assert set(sup.verdicts) == {"XAUUSD"}
