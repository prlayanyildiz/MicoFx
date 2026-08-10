"""A non-positive balance must not silently disarm the daily loss breaker.

rollover() treats ``start_balance > 0`` as its "already anchored today" flag,
so anchoring at 0 left that flag false and made every following cycle roll
over again. Each repeat cleared ``halted``/``loss_halted``, and because
Engine._handle_daily_rollover keys off the return value, it also wiped every
per-symbol sticky halt. Meanwhile pnl_pct() returns a flat 0.0 while
start_balance <= 0, so check() could never re-trip: the breaker was off for
the rest of the session, on the one account state where it matters most.

Holding the previous anchor and halt state is the fail-closed answer.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SystemConfig
from micofx.risk import DailyGuard

DAY = 1_700_000_000.0        # some fixed epoch; the exact day does not matter
NEXT_DAY = DAY + 86_400.0


class _FakeStore:
    """Settings-only store: DailyGuard persists its state through these."""

    def __init__(self) -> None:
        self.data: dict = {}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _guard() -> DailyGuard:
    return DailyGuard(_FakeStore())


def _sys_cfg() -> SystemConfig:
    cfg = SystemConfig()
    cfg.daily_loss_pct = 3.0
    cfg.daily_profit_pct = 0.0
    return cfg


def test_zero_balance_does_not_anchor():
    g = _guard()
    assert g.rollover(DAY, 0.0) is False
    assert g.start_balance == 0.0


def test_zero_balance_does_not_re_roll_every_cycle():
    """The repeat is what cleared the halt over and over."""
    g = _guard()
    assert g.rollover(DAY, 10_000.0) is True      # normal anchor
    g.check(9_000.0, _sys_cfg())                  # -10% -> loss halt
    assert g.halted and g.loss_halted

    # Balance now reads 0 (a failed/blown account read). Every later cycle
    # must be a no-op, not a fresh rollover that clears the halt.
    for _ in range(50):
        assert g.rollover(DAY, 0.0) is False
    assert g.halted, "halt was cleared by a zero-balance rollover"
    assert g.loss_halted


def test_a_halt_survives_a_zero_balance_on_a_new_day_too():
    """Fail closed across the day boundary as well - no anchor, no clear."""
    g = _guard()
    g.rollover(DAY, 10_000.0)
    g.check(9_000.0, _sys_cfg())
    assert g.halted

    assert g.rollover(NEXT_DAY, 0.0) is False
    assert g.halted, "new day + unusable balance must not clear the halt"


def test_a_real_balance_arriving_later_anchors_normally():
    """The guard is a deferral, not a permanent refusal to roll over."""
    g = _guard()
    g.rollover(DAY, 10_000.0)
    g.check(9_000.0, _sys_cfg())
    assert g.halted

    assert g.rollover(NEXT_DAY, 0.0) is False     # still unusable
    assert g.rollover(NEXT_DAY, 8_500.0) is True  # broker came back
    assert g.start_balance == 8_500.0
    assert not g.halted and not g.loss_halted


@pytest.mark.parametrize("balance", [0.0, -1.0, -5_000.0])
def test_negative_balance_is_treated_the_same(balance):
    g = _guard()
    assert g.rollover(DAY, balance) is False
    assert g.start_balance == 0.0


def test_normal_rollover_is_unchanged():
    g = _guard()
    assert g.rollover(DAY, 10_000.0) is True
    assert g.rollover(DAY, 10_000.0) is False     # same day, already anchored
    assert g.rollover(NEXT_DAY, 10_500.0) is True
    assert g.start_balance == 10_500.0


def test_breaker_still_trips_after_a_zero_balance_episode():
    """The point of holding the anchor: the breaker has to still work."""
    g = _guard()
    g.rollover(DAY, 10_000.0)
    for _ in range(10):
        g.rollover(DAY, 0.0)                      # unusable reads in between
    verdict = g.check(9_600.0, _sys_cfg())         # -4%, past the 3% limit
    assert verdict.ok is False
    assert g.loss_halted
