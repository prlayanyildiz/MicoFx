"""A settings row with the wrong shape must not stop the app starting.

get_setting() guards the stored value being unparseable JSON. It does not
guard the value being the wrong TYPE, and every caller assumes one: the
engine's restore block calls .items() on five settings and int()/float() on
two more, all inside __init__. A list where a dict belongs is perfectly valid
JSON, so it sails past the decode guard and takes the constructor down with
an AttributeError - and under pythonw.exe that traceback goes to a stream
nobody reads, so the app simply never appears.

store.__init__ already refuses to allow exactly this for a corrupt DB *file*,
raising a readable RuntimeError instead so run.py can report it. The settings
inside the file had no equivalent. The element-level guards that were there
(``if str(t).isdigit()``, ``if isinstance(v, dict)``) show the intent had
already been considered - it just stopped one level short, at the container.

Nothing the app writes produces these. They come from a restored backup whose
shape predates a rename, a hand-edited row, or a future writer bug - and the
cost of being wrong is a bot that silently does not start.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import store as store_module
from micofx.engine import Engine
from micofx.store import Store


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass

    def min_stop_distance(self, symbol):
        return 0.0

    def info(self, symbol):
        return None

    def resolve(self, symbol):
        return symbol

    def tick(self, symbol):
        return None

    def account(self):
        return {}

    def bars(self, *a, **k):
        return None


CORRUPT = [
    # container is the wrong type entirely
    ("weekend_pending_tickets", 5),
    ("weekend_pending_tickets", "123"),
    ("force_flat_pending_tickets", 7),
    ("secondary_tickets", 9),
    ("secondary_orphan_tickets", 3),
    ("secondary_orphan_scan", ["not", "a", "dict"]),
    ("secondary_orphan_scan", "text"),
    ("symbol_daily_halted", ["x"]),
    ("symbol_daily_halted", 42),
    ("entry_cooldowns", ["x"]),
    ("entry_cooldowns", 1.5),
    ("filled_bars", ["x"]),
    # container fine, element wrong - the length check alone passed these
    ("filled_bars", {"XAUUSD": ["sig", "not-a-number"]}),
    ("filled_bars", {"XAUUSD": [None, None]}),
    ("filled_bars", {"XAUUSD": ["sig"]}),
    # scalars that get coerced
    ("day_start_balance", "cok"),
    ("day_start_balance", ["x"]),
    ("day_start_login", "cok"),
    ("day_start_login", ["x"]),
]


@pytest.mark.parametrize("key,value", CORRUPT,
                         ids=[f"{k}={type(v).__name__}" for k, v in CORRUPT])
def test_a_corrupt_setting_does_not_stop_the_engine_starting(key, value, tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "corrupt.db")
    store = Store()
    store.set_setting(key, value)

    engine = Engine(store, _Client())      # must not raise

    # ...and the bad value must not have been half-adopted either.
    assert isinstance(engine._weekend_pending, set)
    assert isinstance(engine._orphan_scan, dict)
    assert isinstance(engine._cooldowns, dict)
    assert isinstance(engine._filled_bars, dict)
    store.close()


def test_healthy_settings_are_still_restored(tmp_path, monkeypatch):
    """The guard must not quietly discard good state on every start."""
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "good.db")
    store = Store()
    store.set_setting("weekend_pending_tickets", [111, 222])
    store.set_setting("secondary_tickets", [333])
    store.set_setting("entry_cooldowns", {"XAUUSD": 1786400000.0})
    store.set_setting("filled_bars", {"XAUUSD": ["primary", 1786399999]})

    engine = Engine(store, _Client())

    assert engine._weekend_pending == {111, 222}
    assert engine._sec_tickets == {333}
    assert engine._cooldowns == {"XAUUSD": 1786400000.0}
    # Kept per (symbol, leg) now, so a secondary fill cannot erase the
    # primary's already-taken bar. The single-slot shape written by older
    # versions is migrated on read rather than dropped.
    assert engine._filled_bars == {"XAUUSD": {"primary": 1786399999}}
    store.close()


# ------------------------------------------------------- the shape guards

def test_the_guards_fall_back_instead_of_raising():
    assert store_module.as_list({"a": 1}) == []
    assert store_module.as_list([1, 2]) == [1, 2]
    assert store_module.as_dict([1, 2]) == {}
    assert store_module.as_dict({"a": 1}) == {"a": 1}
    assert store_module.as_number("metin", 7.5) == 7.5
    assert store_module.as_number(3) == 3.0
    assert store_module.as_number(2.5) == 2.5


def test_a_bool_is_not_a_number():
    """bool subclasses int; True where an epoch belongs is a shape error."""
    assert store_module.as_number(True, 9.0) == 9.0
    assert store_module.as_number(False, 9.0) == 9.0


def test_a_missing_value_takes_the_default_quietly():
    """None means "never written", which is not a corruption to warn about."""
    assert store_module.as_dict(None) == {}
    assert store_module.as_list(None) == []
    assert store_module.as_number(None, 4.25) == 4.25


def test_the_guards_are_module_functions_not_store_methods():
    """Pins the design choice.

    DailyGuard, Engine and Supervisor are all built with duck-typed fake
    stores in these tests. Putting the guards on Store would make every one
    of those fakes a required update for a guard unrelated to what it tests -
    which is exactly what happened on the first attempt, breaking 22 tests in
    test_core.py alone.
    """
    for name in ("as_dict", "as_list", "as_number"):
        assert callable(getattr(store_module, name))
        assert not hasattr(Store, name)
