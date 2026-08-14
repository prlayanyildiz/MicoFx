"""The lookup tables that must not answer an unknown key in silence.

Test-side, deliberately: the probes call each table with a key that is not in
it, which emits WARNs. That belongs nowhere near a running bot - it lived in
``micofx/`` for one revision and nothing in production ever imported it.

A new table belongs in ``LOOKUPS``. The test walks this list; a table that
is not listed here is invisible to it, so the list is the contract.
"""
from __future__ import annotations

from typing import Callable

from micofx import mt5client
from micofx import strategy as strat
from micofx.logbus import LOG
from micofx.models import READABLE_TIMEFRAMES, STRATEGIES, TIMEFRAMES

# Names the class-protection test requires. Adding a table without adding
# its name here is how the next silent fallback would hide.
REQUIRED = (
    "timeframe_seconds",
    "timeframe_const",
    "_FAMILIES",
    "TIMEFRAMES",
    "READABLE_TIMEFRAMES",
    "STRATEGIES",
)


def _warn_or_raise(name: str, key: str, warned: list) -> None:
    if not warned:
        raise AssertionError(f"{name} swallowed unknown {key!r} with no WARN")


def _probe_timeframe_seconds(capture: Callable) -> None:
    mt5client._TF_SECONDS_WARNED.discard("___NOPE___")
    mt5client.timeframe_seconds("___NOPE___")
    _warn_or_raise("timeframe_seconds", "___NOPE___", capture())


def _probe_timeframe_const(capture: Callable) -> None:
    mt5client.timeframe_const("___NOPE___")
    _warn_or_raise("timeframe_const", "___NOPE___", capture())


def _probe_families(capture: Callable) -> None:
    import numpy as np
    n = 40
    close = np.linspace(100.0, 101.0, n)
    cache = strat.IndicatorCache(close + 0.1, close - 0.1, close, None, 300,
                                 close, np.ones(n), None)
    strat._UNKNOWN_FAMILIES.discard("___NOPE___")
    strat.compute(cache, strat.Params(strategy="___NOPE___"))
    _warn_or_raise("_FAMILIES", "___NOPE___", capture())


def _probe_menu(name: str, menu: list[str], key: str = "___NOPE___") -> None:
    """A menu is not a fallback table: unknown must not be a member."""
    if key in menu:
        raise AssertionError(f"{name} treats {key!r} as a known entry")


LOOKUPS: list[tuple[str, Callable[[Callable], None]]] = [
    ("timeframe_seconds", _probe_timeframe_seconds),
    ("timeframe_const", _probe_timeframe_const),
    ("_FAMILIES", _probe_families),
    ("TIMEFRAMES", lambda _c: _probe_menu("TIMEFRAMES", TIMEFRAMES)),
    ("READABLE_TIMEFRAMES", lambda _c: _probe_menu("READABLE_TIMEFRAMES", READABLE_TIMEFRAMES)),
    ("STRATEGIES", lambda _c: _probe_menu("STRATEGIES", STRATEGIES)),
]


def probe_all(emit_sink: list) -> None:
    """Run every registered probe. ``emit_sink`` collects (msg, level)."""
    orig = LOG.emit

    def _cap(msg: str, level: str = "INFO", symbol: str = "") -> None:
        emit_sink.append((str(msg), str(level)))
        return orig(msg, level, symbol)

    LOG.emit = _cap
    try:
        for name, fn in LOOKUPS:
            before = len(emit_sink)
            fn(lambda: [row for row in emit_sink[before:] if row[1] == "WARN"])
    finally:
        LOG.emit = orig
