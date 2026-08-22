"""Slippage samples from deleted symbols must not shape the portfolio figure.

stats() folds every stored row into one number that answers "is our execution
any good". Restore loaded whatever the blob held, including instruments that
had left the book, so that answer was partly about symbols nobody trades.
Measured on the live database on 22.08: four deleted names held 96 of 575
rows, seventeen percent of the sample. The effect on the number itself was
0.0002 R against a 0.05 R warning threshold, so no verdict was ever wrong -
the share is the problem, not that day's answer.

engine._flush_spread_ratio already prunes its own per-symbol histogram this
way, with the same reasoning written beside it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.execution import ExecutionMonitor


class _Store:
    def __init__(self, symbols, blob):
        self.symbols = symbols
        self.settings = {"execution_samples": blob}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


def _rows(n, r):
    return [{"t": 1.0, "leg": "entry", "adverse": 0.1, "r": r} for _ in range(n)]


BLOB = {"GER40": _rows(3, -0.001), "UK100": _rows(2, 0.05), "FRA40": _rows(1, 0.05)}


def test_a_symbol_that_left_the_book_is_not_restored():
    mon = ExecutionMonitor(_Store({"GER40": object()}, BLOB))
    assert set(mon._samples) == {"GER40"}
    assert mon.stats()["total"]["samples"] == 3, "toplam yalniz kitaptakileri saymali"


def test_a_disabled_symbol_is_still_in_the_book_and_keeps_its_samples():
    """Disabled is not deleted - store.symbols still holds it."""
    mon = ExecutionMonitor(_Store({"GER40": object(), "UK100": object()}, BLOB))
    assert set(mon._samples) == {"GER40", "UK100"}


def test_an_empty_book_does_not_wipe_the_history():
    """A blank lookup is not a reason to throw away every stored sample."""
    mon = ExecutionMonitor(_Store({}, BLOB))
    assert set(mon._samples) == {"GER40", "UK100", "FRA40"}


def test_the_pruned_set_is_what_gets_written_back():
    store = _Store({"GER40": object()}, BLOB)
    mon = ExecutionMonitor(store)
    mon._persist(force=True)
    assert set(store.settings["execution_samples"]) == {"GER40"}
