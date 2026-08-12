"""A full scan searches the book, not the symbols that are switched off.

``supervisor._maybe_reoptimize`` skips a disabled symbol outright. ``start()``
took ``list(store.symbols)``, which includes them - the third instance today of
a policy the system states and then applies on only one of the two paths that
can break it.

EURUSD has been off all day and was searched seven times, taking a slice of
every eighteen-minute run and picking up two applied configurations while
switched off. Both Cursor and this scan flagged it as an anomaly on separate
rounds before the cause was found, which is the other cost: it looks like a
fault every time someone reads the log.

Naming a symbol explicitly still searches it. "Optimise EURUSD before I turn it
on" is a real thing to want, and asking for it by name is unambiguous; asking
for "everything" is not a request for the symbols you have already excluded.

Refined later, from a VDS install: that last sentence needs something to have
been excluded FROM. With nothing enabled at all there is no such intent to
respect, and the rule closed a loop instead of expressing one - seed_symbols
forces every seeded symbol disabled, _require_optimised_before_enabling refuses
to switch one on until it has been searched, and "everything" resolved to the
enabled ones, of which there were none. Naming all ten by hand was the only way
in. So an all-disabled book now searches the whole book; the exclusion below
still holds the moment anything is enabled, which is the case the rule was
written for. Nothing is granted by it either: naming the same symbols already
ran exactly that, and auto-reopt never reaches this path (it queues by name and
skips disabled symbols before it gets there).
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

def test_a_full_scan_leaves_a_disabled_symbol_out():
    res = _targets(_opt())
    assert res["ok"] is True
    assert "EURUSD" not in res["job"]["symbols"]
    assert set(res["job"]["symbols"]) == {"GER40", "US30"}


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


def test_one_enabled_symbol_is_enough_to_restore_the_exclusion():
    """The boundary: the moment anything is on, an off symbol is a deliberate
    exclusion again and a full scan leaves it alone."""
    opt = _opt()
    for cfg in opt.store.symbols.values():
        cfg.enabled = False
    opt.store.symbols["GER40"].enabled = True
    assert _targets(opt)["job"]["symbols"] == ["GER40"]


def test_an_unknown_name_is_still_dropped():
    res = _targets(_opt(), symbols=["GER40", "YOKBOYLE"])
    assert res["job"]["symbols"] == ["GER40"]
