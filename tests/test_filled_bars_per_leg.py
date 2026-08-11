"""A secondary fill must not erase the primary's already-taken bar.

_filled_bars is the only thing standing between a restart and a second
position on the same signal: SymbolState is rebuilt empty on every start, the
signal recomputes identically off the same still-last-closed bar, and the
post-fill cooldown is 2 minutes against a 5-60 minute bar. The code carries
the live incident it was written for:

    19:00:27 NAS100 BUY @ 29728.00
    19:01:22 restart
    19:09:26 NAS100 BUY @ 29705.90   (same M30 bar, cooldown long gone)
    both stopped out for -14.22 each

It kept one slot per symbol, on the assumption that "a symbol only ever fills
off whichever leg is currently driving". That does not hold once the ensemble
is on and max_positions allows more than one: the primary fills and records
its bar, the secondary then fills and overwrites the whole entry, and the
primary's already-taken bar is unguarded again. A restart inside that bar
re-enters it - the same double entry, reached through the other leg.

Now keyed per (symbol, leg). The single-slot shape is migrated rather than
dropped, so the guard keeps covering whichever leg it had recorded across the
restart that installs this change.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine

PRIMARY_BAR = 1786400000
SECONDARY_BAR = 1786401800


class _Store:
    def __init__(self, symbols=("NAS100",)):
        self.saved = {}
        self.symbols = {s: object() for s in symbols}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)

    def set_setting(self, key, value):
        self.saved[key] = value


def _engine(store=None):
    eng = object.__new__(Engine)
    eng.store = store or _Store()
    eng._filled_bars = {}
    return eng


def _restore(store):
    """Exactly what Engine.__init__ does with the persisted blob."""
    eng = object.__new__(Engine)
    eng.store = store
    eng._filled_bars = {}

    def ok(bar):
        return isinstance(bar, (int, float)) and not isinstance(bar, bool)

    for sym, value in (store.get_setting("filled_bars", {}) or {}).items():
        legs = {}
        if isinstance(value, dict):
            legs = {str(k): int(v) for k, v in value.items() if ok(v)}
        elif isinstance(value, (list, tuple)) and len(value) == 2 and ok(value[1]):
            legs = {str(value[0]): int(value[1])}
        if legs:
            eng._filled_bars[str(sym)] = legs
    return eng


def _blocked(eng, symbol, source, bar):
    """The check _evaluate runs before offering an entry."""
    return eng._filled_bars.get(symbol, {}).get(source) == bar


# ------------------------------------------------------------- the bug

def test_a_secondary_fill_does_not_unguard_the_primary_bar():
    eng = _engine()
    eng._mark_bar_filled("NAS100", "primary", PRIMARY_BAR)
    eng._mark_bar_filled("NAS100", "secondary", SECONDARY_BAR)
    assert _blocked(eng, "NAS100", "primary", PRIMARY_BAR)
    assert _blocked(eng, "NAS100", "secondary", SECONDARY_BAR)


def test_the_primary_bar_stays_guarded_across_a_restart():
    """The restart is the whole point of persisting this."""
    eng = _engine()
    eng._mark_bar_filled("NAS100", "primary", PRIMARY_BAR)
    eng._mark_bar_filled("NAS100", "secondary", SECONDARY_BAR)
    revived = _restore(eng.store)
    assert _blocked(revived, "NAS100", "primary", PRIMARY_BAR)


def test_the_reverse_order_too():
    eng = _engine()
    eng._mark_bar_filled("NAS100", "secondary", SECONDARY_BAR)
    eng._mark_bar_filled("NAS100", "primary", PRIMARY_BAR)
    assert _blocked(_restore(eng.store), "NAS100", "secondary", SECONDARY_BAR)


# ------------------------------------------------- what must keep working

def test_a_new_bar_on_the_same_leg_supersedes_the_old_one():
    eng = _engine()
    eng._mark_bar_filled("NAS100", "primary", PRIMARY_BAR)
    eng._mark_bar_filled("NAS100", "primary", PRIMARY_BAR + 1800)
    assert not _blocked(eng, "NAS100", "primary", PRIMARY_BAR)
    assert _blocked(eng, "NAS100", "primary", PRIMARY_BAR + 1800)


def test_an_unfilled_bar_is_never_blocked():
    eng = _engine()
    eng._mark_bar_filled("NAS100", "primary", PRIMARY_BAR)
    assert not _blocked(eng, "NAS100", "primary", PRIMARY_BAR + 1800)
    assert not _blocked(eng, "NAS100", "secondary", PRIMARY_BAR)
    assert not _blocked(eng, "GER40", "primary", PRIMARY_BAR)


def test_a_zero_bar_is_not_recorded():
    eng = _engine()
    eng._mark_bar_filled("NAS100", "primary", 0)
    assert eng._filled_bars == {}


def test_symbols_no_longer_in_the_portfolio_are_dropped():
    eng = _engine(_Store(symbols=("NAS100",)))
    eng._mark_bar_filled("NAS100", "primary", PRIMARY_BAR)
    eng._mark_bar_filled("SILINDI", "primary", PRIMARY_BAR)
    assert "SILINDI" not in eng._filled_bars
    assert "NAS100" in eng._filled_bars


def test_a_write_failure_never_reaches_the_order_path():
    class _Broken(_Store):
        def set_setting(self, key, value):
            raise RuntimeError("disk dolu")

    eng = _engine(_Broken())
    eng._mark_bar_filled("NAS100", "primary", PRIMARY_BAR)   # must not raise


# ----------------------------------------------------------- migration

def test_the_single_slot_shape_is_migrated_not_dropped():
    """Otherwise the restart that ships this fix arrives unguarded."""
    store = _Store()
    store.saved["filled_bars"] = {"NAS100": ["primary", PRIMARY_BAR]}
    assert _blocked(_restore(store), "NAS100", "primary", PRIMARY_BAR)


@pytest.mark.parametrize("blob", [
    {"NAS100": ["sig", "yok"]},          # bar is not a number
    {"NAS100": ["primary"]},             # short
    {"NAS100": "merhaba"},
    {"NAS100": None},
    {"NAS100": {"primary": "yok"}},
    {"NAS100": {"primary": True}},       # bool is not a bar
    {"NAS100": []},
])
def test_a_corrupt_blob_does_not_stop_start_up(blob):
    store = _Store()
    store.saved["filled_bars"] = blob
    eng = _restore(store)                 # must not raise
    assert not _blocked(eng, "NAS100", "primary", PRIMARY_BAR)
