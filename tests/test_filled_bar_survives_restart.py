"""A restart must not take the same bar's signal a second time.

The post-fill cooldown was supposed to cover this and does not: it is 2
minutes, while a bar is 5 to 60, so a restart even slightly later walks
straight past it. Live, hours after the cooldown was made persistent:

    19:00:27 [NAS100] BUY 0.3 @ 29728.00 SL=29680.60
    19:00:27 [US500]  BUY 0.3 @ 7767.70  SL=7759.90
    19:01:22 Yeniden baslatma istegi alindi.
    19:09:26 [NAS100] BUY 0.3 @ 29705.90 SL=29658.50
    19:09:26 [US500]  BUY 0.3 @ 7763.80  SL=7756.00
    19:32    all four stopped out: -14.22, -14.22, -2.34, -2.34

NAS100 runs M30, so at 19:09 the bar that closed at 19:00 was still the last
closed one. The signal recomputed identically and fired again, eight minutes
after a two-minute cooldown had expired. The duplicates cost -16.56.

What actually prevents it is the fact that this bar's signal was already
filled - and that lived only in SymbolState, which a restart rebuilds empty.
"""
from __future__ import annotations

from micofx.engine import Engine


class _Store:
    def __init__(self, symbols=("NAS100", "US500")):
        self.settings: dict[str, object] = {}
        self.symbols = {s: object() for s in symbols}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


def _engine(store):
    eng = Engine.__new__(Engine)
    eng.store = store
    eng._filled_bars = {
        str(k): [str(v[0]), int(v[1])]
        for k, v in (store.get_setting("filled_bars") or {}).items()
        if isinstance(v, (list, tuple)) and len(v) == 2
    }
    return eng


BAR = 1_786_000_000          # the M30 bar that closed at 19:00


def test_the_filled_bar_is_remembered_across_a_restart():
    store = _Store()
    _engine(store)._mark_bar_filled("NAS100", "primary", BAR)

    # ...process dies and comes back.
    assert _engine(store)._filled_bars["NAS100"] == ["primary", BAR]


def test_the_same_bar_is_refused_after_the_restart():
    store = _Store()
    _engine(store)._mark_bar_filled("NAS100", "primary", BAR)
    eng = _engine(store)
    # The exact comparison _ready_for_entry makes.
    assert eng._filled_bars.get("NAS100") == ["primary", BAR]


def test_the_next_bar_is_allowed():
    store = _Store()
    _engine(store)._mark_bar_filled("NAS100", "primary", BAR)
    eng = _engine(store)
    assert eng._filled_bars.get("NAS100") != ["primary", BAR + 1800]


def test_the_other_leg_on_the_same_bar_is_allowed():
    # Primary and secondary are different signals; one filling does not
    # consume the other's turn.
    store = _Store()
    _engine(store)._mark_bar_filled("NAS100", "primary", BAR)
    eng = _engine(store)
    assert eng._filled_bars.get("NAS100") != ["secondary", BAR]


def test_another_symbol_is_unaffected():
    store = _Store()
    _engine(store)._mark_bar_filled("NAS100", "primary", BAR)
    assert _engine(store)._filled_bars.get("US500") is None


def test_a_later_fill_supersedes_the_earlier_one():
    store = _Store()
    eng = _engine(store)
    eng._mark_bar_filled("NAS100", "primary", BAR)
    eng._mark_bar_filled("NAS100", "primary", BAR + 1800)
    assert _engine(store)._filled_bars["NAS100"] == ["primary", BAR + 1800]


def test_deleted_symbols_are_pruned():
    store = _Store()
    eng = _engine(store)
    eng._mark_bar_filled("NAS100", "primary", BAR)
    eng._mark_bar_filled("US500", "primary", BAR)
    store.symbols.pop("US500")            # symbol removed from the portfolio
    eng._mark_bar_filled("NAS100", "primary", BAR + 1800)
    assert set(store.get_setting("filled_bars")) == {"NAS100"}


def test_a_missing_bar_timestamp_records_nothing():
    # bar 0 means "no closed bar known" - recording it would block the symbol
    # against a key it can never match again.
    store = _Store()
    eng = _engine(store)
    eng._mark_bar_filled("NAS100", "primary", 0)
    assert store.get_setting("filled_bars") is None


def test_a_corrupt_stored_row_is_ignored_not_fatal():
    store = _Store()
    store.set_setting("filled_bars", {"NAS100": "bozuk", "US500": ["primary", BAR]})
    assert set(_engine(store)._filled_bars) == {"US500"}


def test_a_write_failure_never_reaches_the_caller():
    # Runs on the order path, right after a fill and before the TRADE line.
    class _Broken(_Store):
        def set_setting(self, key, value):
            raise RuntimeError("disk full")

    eng = _engine(_Broken())
    eng._mark_bar_filled("NAS100", "primary", BAR)      # must not raise
