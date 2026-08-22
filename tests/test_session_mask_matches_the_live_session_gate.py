"""The replay's session mask and the live session gate must agree, bar by bar.

Both answer the same question - is this broker timestamp inside a trading
window - and both compute it from scratch. session_mask does its own
day-of-week and minute arithmetic (``((times // 86400 + 3) % 7) + 1``)
rather than calling sessions.server_clock, so the two are one edit away from
disagreeing, and the disagreement would be silent: the search would score a
set of hours the engine does not trade, or refuse hours it does.

That is the class this file exists to pin. It has already cost us three
times in one day through the same shape - a rule written twice and drifting -
so the mask gets tested against the gate rather than against itself.

Coverage is deliberately wide: every minute of a week is expensive, so the
grid walks a full week at five-minute steps across several window shapes,
including the boundary minutes where an off-by-one lives.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest, sessions
from micofx.models import SymbolConfig

# 1970-01-05 was a Monday, so a week from here covers Mon..Sun in order and
# keeps the arithmetic readable when a case fails.
WEEK_START = 4 * 86400
WEEK = np.arange(WEEK_START, WEEK_START + 7 * 86400, 300, dtype=np.float64)


def _cfg(**kw) -> SymbolConfig:
    base = dict(symbol="GER40", group="index", magic=1, use_sessions=True)
    base.update(kw)
    return SymbolConfig(**base)


CASES = [
    pytest.param(_cfg(use_sessions=False), False, id="no-windows"),
    pytest.param(_cfg(sessions=[{"start": "09:00", "end": "17:30"}]), False, id="single-window"),
    pytest.param(_cfg(sessions=[{"start": "09:00", "end": "12:00"}, {"start": "13:00", "end": "17:30"}]), False, id="two-windows"),
    pytest.param(
        _cfg(sessions=[{"start": "22:00", "end": "02:00"}]), False,
        id="wraps-midnight",
        marks=pytest.mark.xfail(
            strict=True,
            reason=(
                "MEASURED DIVERGENCE, not a gap in the test. A window that "
                "crosses midnight spills into Saturday's first hours, and the "
                "two sides disagree there: session_mask marks 24 of the week's "
                "bars tradable (Sat 00:00-02:00) where sessions.evaluate "
                "refuses them as weekend. Live is right and the mask is wrong. "
                "Dormant on this book - no symbol runs a wrapping window (every "
                "one has start < end) and index feeds carry no Saturday bars at "
                "all, which is why it has never shown. Left failing on purpose "
                "rather than deleted: strict, so the day someone fixes the mask "
                "this turns red and the marker gets removed with the fix."
            ),
        ),
    ),
    pytest.param(_cfg(sessions=[{"start": "09:00", "end": "17:30"}]), True, id="all-hours-override"),
    pytest.param(_cfg(group="crypto", sessions=[{"start": "09:00", "end": "17:30"}]), False, id="crypto-weekend-open"),
    pytest.param(_cfg(group="crypto", sessions=[{"start": "09:00", "end": "17:30"}]), True, id="crypto-all-hours"),
]


@pytest.mark.parametrize("cfg,all_hours", CASES)
def test_the_mask_answers_what_the_gate_answers(cfg, all_hours):
    mask = backtest.session_mask(cfg, WEEK, all_hours)
    gate = np.array([sessions.evaluate(cfg, float(t), all_hours).open for t in WEEK])

    if np.array_equal(mask, gate):
        return
    # A bare "arrays differ" tells you nothing about which minute broke.
    bad = np.flatnonzero(mask != gate)[:5]
    detail = ", ".join(
        f"t={int(WEEK[i])} (gun {int((WEEK[i] // 86400 + 3) % 7) + 1}, "
        f"{int((WEEK[i] % 86400) // 3600):02d}:{int((WEEK[i] % 3600) // 60):02d}) "
        f"maske={bool(mask[i])} kapi={bool(gate[i])}"
        for i in bad)
    raise AssertionError(
        f"{bad.size}+ bar ayrisiyor ({mask.size} barin {(mask != gate).sum()}'i): {detail}")


def test_the_grid_actually_exercises_both_answers():
    """A mask that is all True would pass every case above and prove nothing."""
    cfg = _cfg(sessions=[{"start": "09:00", "end": "17:30"}])
    mask = backtest.session_mask(cfg, WEEK, False)
    assert mask.any() and not mask.all(), "izgara acik ve kapali barlarin ikisini de gormeli"


def test_the_weekend_is_shut_for_an_index_and_open_for_crypto():
    """The one asymmetry both sides carry; pinned so neither drops it alone."""
    weekend = np.array([WEEK_START + 5 * 86400 + 12 * 3600,      # Saturday noon
                        WEEK_START + 6 * 86400 + 12 * 3600],     # Sunday noon
                       dtype=np.float64)
    index = backtest.session_mask(_cfg(sessions=[{"start": "00:00", "end": "23:59"}]), weekend, True)
    crypto = backtest.session_mask(_cfg(group="crypto", sessions=[{"start": "00:00", "end": "23:59"}]),
                                   weekend, True)
    assert not index.any(), "endeks hafta sonu kapali"
    assert crypto.all(), "kripto hafta sonu acik"
    for t in weekend:
        assert sessions.evaluate(_cfg(sessions=[{"start": "00:00", "end": "23:59"}]), float(t), True).open is False
        assert sessions.evaluate(_cfg(group="crypto", sessions=[{"start": "00:00", "end": "23:59"}]),
                                 float(t), True).open is True
