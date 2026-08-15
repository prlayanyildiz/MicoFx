"""A halved history window must not be silent.

The planner asks for max_bars and the terminal answers with nothing at all when
it cannot serve that many - not with fewer bars. The halving loop exists for
exactly that and is right: it keeps stepping down until the terminal answers,
so a timeframe is searched on what history exists rather than dropped. M5 was
never once searched across 104 recorded runs before that loop was added.

What was missing is the announcement. A symbol that quietly falls back to half
the window is compared, in the same run and the same table, against symbols that
got the full one - the run record reads as though they were measured equally.
That is the same silent-substitution shape as timeframe_seconds returning 300,
the M1 request returning M5 bars, and the cost stamp reading the clock.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer

SRC = inspect.getsource(Optimizer._plan_symbol)


def test_the_halving_loop_is_still_there():
    """Removing it drops whole timeframes instead of shortening them."""
    assert "want //= 2" in SRC
    assert "len(got) < 600" in SRC


def test_the_request_is_remembered_before_halving():
    assert "asked = want" in SRC, "nothing to compare the final want against"


def test_a_shortened_window_warns():
    body = SRC[SRC.index("asked = want"):]
    assert "if want < asked:" in body
    warn = body[body.index("if want < asked:"):][:600]
    assert "WARN" in warn, "a shortened window is a warning, not an info line"
    assert "bar istendi" in warn and "arandi" in warn, (
        "the message has to carry both numbers to be worth reading")


def test_the_full_window_stays_quiet():
    """Every symbol every run would otherwise narrate itself."""
    body = SRC[SRC.index("asked = want"):]
    guard = body.index("if want < asked:")
    emit = body.index("LOG.emit")
    assert guard < emit, "the warning must sit inside the shortened branch"
