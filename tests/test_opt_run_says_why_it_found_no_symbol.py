""""No symbol selected" must not be the answer to a request that named some.

Reported from the panel: with symbols picked in the optimiser's chip picker,
starting a run answered "Sembol secilmedi." - no symbol selected.

The picker's selection is a module-level Set that outlives the symbol list. A
name picked before the book was cut from twenty symbols to ten stays in that
Set; the chips re-render off the live list, but the Set is never reconciled
against it. So the request names several symbols, ``start`` filters every one of
them out against ``store.symbols``, ``targets`` comes back empty, and the panel
reports that nothing was selected. Nothing on screen contradicts it either: the
"Tumu" chip only lights when the selection is empty, and it is not.

Reproduced against the live endpoint before touching anything - POST
/api/opt/run with two names no longer in the book returned exactly that string,
without starting a run.

One message was serving three situations and was wrong about two:

  * names given, none of them in the book -> say which names, and that the
    selection may be stale;
  * nothing given and every symbol disabled -> say that, since "select one"
    is not the fix;
  * nothing given and no symbols at all -> the original message, which is the
    only case it was ever true for.

The picker prunes the stale names too, so the selection empties rather than
going unmatched - and an empty selection is exactly "Tumu", which runs the book.
That is the actual repair; the message is what makes the next variant of this
legible instead of misleading.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


class _Thread:
    """``busy`` is a read-only property over the worker thread, so the busy
    case is set by handing it one that says it is alive."""

    def __init__(self, alive):
        self._alive = alive

    def is_alive(self):
        return self._alive

    def start(self):
        pass


class _Store:
    def __init__(self, symbols):
        # Production reads store.system.charge_costs (optimizer.py:1005).
        # The real dataclass, not a stub: a stub only carries the field
        # production happens to touch today and drifts again on the next
        # one. This double was stale enough that every test in the file
        # died on AttributeError before its assertion - so the guard it
        # contains proved nothing. Added 05.09.
        self.system = SystemConfig()
        self.symbols = {c.symbol: c for c in symbols}

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}


def _opt(symbols) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._lock = threading.RLock()
    opt.store = _Store(symbols)
    opt.job = {}
    opt._cancel = threading.Event()
    opt._force_apply = False
    opt._thread = None
    return opt


def _cfg(symbol, enabled=True):
    c = SymbolConfig(symbol=symbol, magic=abs(hash(symbol)) % 10_000)
    c.enabled = enabled
    return c


BOOK = [_cfg("GER40"), _cfg("NAS100"), _cfg("US30")]


# ------------------------------------------------------------- the defect

def test_naming_symbols_that_left_the_book_says_which_ones():
    res = _opt(BOOK).start(symbols=["EURUSD", "GBPJPY"])
    assert res["ok"] is False
    assert "EURUSD" in res["error"] and "GBPJPY" in res["error"]
    assert "secilmedi" not in res["error"].lower(), (
        "sembol adlandirildi - 'secilmedi' yanlis cevap")


def test_it_points_at_the_stale_selection():
    """The message has to name the fix, since the screen shows nothing lit."""
    err = _opt(BOOK).start(symbols=["EURUSD"])["error"]
    assert "eskimis" in err.lower() or "yenileyin" in err.lower()


def test_a_book_with_everything_switched_off_searches_all_of_it():
    """The bootstrap. A fresh install seeds every symbol disabled and refuses
    to enable one until it has been searched, so "optimise everything" has to
    mean the book here or there is no way in at all."""
    opt = _opt([_cfg("GER40", enabled=False), _cfg("NAS100", enabled=False)])
    opt._run = lambda *a, **k: None
    res = opt.start()
    assert res["ok"] is True
    assert res["job"]["symbols"] == ["GER40", "NAS100"]


def test_a_closed_symbol_beside_an_open_one_is_still_searched():
    """Closing is a decision, not a death sentence - the full scan must
    re-score the off name so a later grid can still produce a candidate."""
    opt = _opt([_cfg("GER40"), _cfg("NAS100", enabled=False)])
    opt._run = lambda *a, **k: None
    assert set(opt.start()["job"]["symbols"]) == {"GER40", "NAS100"}


# --------------------------------------------------- what must keep working

def test_an_empty_book_still_gets_the_original_message():
    """The one situation that message was ever true for."""
    assert _opt([]).start()["error"] == "Sembol secilmedi."


def test_a_partly_stale_selection_still_runs_the_names_it_knows():
    """Not an error at all - the known names are the run."""
    opt = _opt(BOOK)
    opt._run = lambda *a, **k: None          # do not start a real sweep
    res = opt.start(symbols=["EURUSD", "GER40", "GBPJPY"])
    assert res["ok"] is True
    assert res["job"]["symbols"] == ["GER40"]


def test_no_selection_runs_the_whole_book():
    opt = _opt(BOOK + [_cfg("USDCHF", enabled=False)])
    opt._run = lambda *a, **k: None
    res = opt.start()
    assert res["ok"] is True
    assert set(res["job"]["symbols"]) == {"GER40", "NAS100", "US30", "USDCHF"}


def test_naming_a_disabled_symbol_still_searches_it():
    """"optimise this before I turn it on" - asking by name says so."""
    opt = _opt(BOOK + [_cfg("USDCHF", enabled=False)])
    opt._run = lambda *a, **k: None
    res = opt.start(symbols=["USDCHF"])
    assert res["ok"] is True
    assert res["job"]["symbols"] == ["USDCHF"]


def test_a_busy_optimizer_still_refuses_first():
    opt = _opt(BOOK)
    opt._thread = _Thread(alive=True)
    assert "calisiyor" in opt.start(symbols=["EURUSD"])["error"]
