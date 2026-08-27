"""A full scan searches the book, including symbols that are switched off.

The earlier exclusion (off = deliberate skip) closed a loop: a charged-negative
close removed the name from every later ``start()`` with no list, so the symbol
could never be re-scored after the grid moved. Closing is a decision; applying
the winner is not automatic - ``_finish_symbol`` records ``opt_runs`` and leaves
``enabled`` / ``opt_summary`` alone.

Calendar auto-queue is gone. Naming a symbol still searches it even when
``enabled`` is false. An empty book is still "Sembol secilmedi."
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self):
        self.symbols = {
            "GER40": SymbolConfig(symbol="GER40", magic=1, enabled=True),
            "US30": SymbolConfig(symbol="US30", magic=2, enabled=True),
            "EURUSD": SymbolConfig(symbol="EURUSD", magic=3, enabled=False),
        }

    def get_setting(self, key, default=None):
        return default


def _opt() -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = _Store()
    opt._lock = threading.RLock()
    opt._cancel = threading.Event()
    opt.job = {}
    opt._thread = None          # ``busy`` is a property over this
    return opt


def _targets(opt: Optimizer, **kw):
    """start() without letting the worker thread run."""
    started = {}
    opt._run = lambda *a, **k: None                      # type: ignore[assignment]
    original = threading.Thread

    class _NoThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            started["ran"] = True

        def is_alive(self):      # ``busy`` reads this
            return False

    threading.Thread = _NoThread                          # type: ignore[misc]
    try:
        result = opt.start(**kw)
    finally:
        threading.Thread = original                       # type: ignore[misc]
    return result


# --------------------------------------------------------- the whole book only

def test_a_full_scan_includes_a_disabled_symbol():
    res = _targets(_opt())
    assert res["ok"] is True
    assert "EURUSD" in res["job"]["symbols"]
    assert set(res["job"]["symbols"]) == {"GER40", "US30", "EURUSD"}


def test_naming_it_still_searches_it():
    """"Optimise EURUSD before I turn it on" stays possible."""
    res = _targets(_opt(), symbols=["EURUSD"])
    assert res["ok"] is True
    assert res["job"]["symbols"] == ["EURUSD"]


def test_a_named_mix_keeps_everything_named():
    res = _targets(_opt(), symbols=["GER40", "EURUSD"])
    assert set(res["job"]["symbols"]) == {"GER40", "EURUSD"}


def test_a_book_with_nothing_enabled_searches_the_whole_book():
    """The bootstrap case: nothing is enabled, so nothing was excluded either,
    and refusing here is a closed loop rather than a policy."""
    opt = _opt()
    for cfg in opt.store.symbols.values():
        cfg.enabled = False
    res = _targets(opt)
    assert res["ok"] is True
    assert set(res["job"]["symbols"]) == {"GER40", "US30", "EURUSD"}


def test_one_enabled_symbol_does_not_drop_the_rest():
    """The old boundary: one name on used to hide every off name. That is
    the loop this file now guards against."""
    opt = _opt()
    for cfg in opt.store.symbols.values():
        cfg.enabled = False
    opt.store.symbols["GER40"].enabled = True
    assert set(_targets(opt)["job"]["symbols"]) == {"GER40", "US30", "EURUSD"}


def test_an_unknown_name_is_still_dropped():
    res = _targets(_opt(), symbols=["GER40", "YOKBOYLE"])
    assert res["job"]["symbols"] == ["GER40"]
