"""A non-list trade_days must not reach a live config: it stops the cycle dead.

_coerce() casts bool/int/float/str fields but assigns everything else
verbatim, and ``trade_days`` is declared ``list``. The guard that followed it
in from_dict() was one-sided - it repaired a list and silently kept anything
else - so an int, a string or a float survived into the config untouched.

Nothing notices until sessions.evaluate() runs ``day in cfg.trade_days``:

    trade_days = 5        -> TypeError: argument of type 'int' is not iterable
    trade_days = "1,2,3"  -> TypeError: 'in <string>' requires string as left
                             operand, not int

That call sits in manage_positions() (via should_flatten), whose only guard is
the loop-level ``except`` in start(). So one corrupt symbol aborted _cycle()
before the daily risk check and before entries, on every single cycle - which
means EVERY open position, on every symbol, stopped being trailed or flattened
and was left riding nothing but its broker-side stop. Permanent, not transient.

The API rejects all of these shapes (see _validate_sessions), so the reachable
ingress is a hand-edited config/defaults.json - which Store.seed feeds straight
through ``SymbolConfig.from_dict(payload)`` - or a mangled settings blob.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import sessions
from micofx.models import SymbolConfig

WEEKDAYS = [1, 2, 3, 4, 5]

# Every one of these crashed sessions.evaluate() before the fix, except the
# dict - which is iterable, so it merely made the symbol permanently closed.
MALFORMED = [5, "1,2,3", "12345", 3.7, True, {"1": True}, ("1", "2"), None]


def _cfg(days):
    return SymbolConfig.from_dict({"symbol": "X", "magic": 1, "trade_days": days})


@pytest.mark.parametrize("days", MALFORMED, ids=[repr(d) for d in MALFORMED])
def test_a_malformed_trade_days_never_survives_into_the_config(days):
    assert _cfg(days).trade_days == WEEKDAYS


@pytest.mark.parametrize("days", MALFORMED, ids=[repr(d) for d in MALFORMED])
def test_and_so_the_session_check_cannot_raise(days):
    """The consequence, stated: this is the call that aborted the cycle."""
    cfg = _cfg(days)
    state = sessions.evaluate(cfg, time.time())
    assert isinstance(state.open, bool)
    sessions.should_flatten(cfg, time.time())


def test_a_list_whose_entries_are_all_invalid_falls_back_too():
    """[] left the symbol shut while the panel reported it opens in 0 minutes."""
    assert _cfg([0, 8, "x", -1]).trade_days == WEEKDAYS
    assert _cfg([]).trade_days == WEEKDAYS


def test_a_good_list_is_still_taken_verbatim():
    assert _cfg([1, 3, 5]).trade_days == [1, 3, 5]
    assert _cfg([7, 6]).trade_days == [6, 7]
    # Strings that spell a valid day still parse - stored blobs carry them.
    assert _cfg(["1", "2"]).trade_days == [1, 2]
    # Mixed: keep what is real, drop what is not.
    assert _cfg([1, 2, 99, "sat"]).trade_days == [1, 2]


def test_an_absent_key_keeps_the_dataclass_default():
    assert SymbolConfig.from_dict({"symbol": "X", "magic": 1}).trade_days == WEEKDAYS


def test_the_shipped_template_has_no_malformed_trade_days():
    """Guards the one file this can actually arrive through."""
    import json

    path = Path(__file__).resolve().parents[1] / "config" / "defaults.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    for entry in data["symbols"]:
        days = entry.get("trade_days")
        if days is None:
            continue
        assert isinstance(days, list) and days, f"{entry['symbol']}: {days!r}"
        for d in days:
            assert isinstance(d, int) and 1 <= d <= 7, f"{entry['symbol']}: {d!r}"
