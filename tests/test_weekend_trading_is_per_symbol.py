"""Weekend trading is a property of the instrument, not of its asset class.

``weekend_closed`` exempted whole groups, and only crypto. That was right until
the book gained BRENTOIL-PERP and GOLD-PERP: both are commodities by group, and
both print bars through the weekend while the spot contracts of the *same*
commodities do not.

Measured 15.08 over 4000 hourly bars per symbol, counting bars stamped Saturday
or Sunday:

    BTCUSD / ETHUSD      28.0%   (2/7 - full weekend)
    BRENTOIL-PERP        9.9%
    GOLD-PERP            9.9%
    SpotBrent            0.0%
    XAUUSD               0.0%
    every index          0.0%

So the perpetuals trade roughly a third of the weekend hours crypto does, and
their spot equivalents trade none. Held shut by the group rule, they lost every
one of those hours - and the operator had added them precisely because they run
when the indices do not.
"""
from __future__ import annotations

import calendar
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import sessions
from micofx.models import SymbolConfig

SATURDAY = calendar.timegm((2026, 8, 15, 12, 0, 0, 0, 0, 0))
WEDNESDAY = calendar.timegm((2026, 8, 12, 12, 0, 0, 0, 0, 0))


def _cfg(group="commodity", weekend_open=False):
    c = SymbolConfig(symbol="X", group=group)
    c.weekend_open = weekend_open
    return c


def test_a_marked_symbol_trades_at_the_weekend():
    assert sessions.weekend_closed(_cfg(weekend_open=True), SATURDAY) is False


def test_its_spot_equivalent_still_does_not():
    """Same group, same commodity, no weekend bars - must stay shut."""
    assert sessions.weekend_closed(_cfg(), SATURDAY) is True


def test_crypto_is_still_exempt_by_group():
    """The existing rule is not replaced, only widened."""
    assert sessions.weekend_closed(_cfg(group="crypto"), SATURDAY) is False


def test_the_flag_changes_nothing_on_a_weekday():
    for weekend_open in (True, False):
        assert sessions.weekend_closed(_cfg(weekend_open=weekend_open),
                                       WEDNESDAY) is False


def test_the_default_is_closed():
    """A new symbol must not start trading weekends because nobody said no."""
    assert SymbolConfig(symbol="X").weekend_open is False


def test_an_old_row_without_the_field_still_loads():
    cfg = SymbolConfig.from_dict({"symbol": "X", "group": "commodity"})
    assert cfg.weekend_open is False
    assert sessions.weekend_closed(cfg, SATURDAY) is True
