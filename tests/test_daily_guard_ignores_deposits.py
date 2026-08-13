"""A deposit is not profit: the daily loss breaker must not be disarmed by one.

Measured live 2026-08-13 20:00. Anchor 1723.44, realised -304.62, floating
+151.29, but balance read 1918.78 - the gap is an external deposit, confirmed
after the fix as exactly +500.00 straight from MT5 deal history.
The breaker anchored on raw equity drift reported **+20.11%** while trading
was **-17.68%**: a 37.8-point error, wider than the entire 33% loss band,
so daily_loss_pct could never fire no matter how much the day lost.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SystemConfig
from micofx.risk import DailyGuard

# Live figures, 2026-08-13 20:00.
START_BALANCE = 1723.44
DEPOSIT = 500.00  # cash_flow_since() read this back live after the fix
REALISED = -304.62
FLOATING = 151.29
# Observed directly, not reconstructed: realised/floating are reported rounded
# to 2dp, so summing the parts lands 0.04 away from what the account actually
# read - and that is enough to move the raw figure across a rounding boundary.
EQUITY = 2070.07


class _FakeStore:
    def __init__(self) -> None:
        self.data: dict = {}
        self.system = SystemConfig()

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _guard(store=None) -> DailyGuard:
    g = DailyGuard(store or _FakeStore())
    g.start_balance = START_BALANCE
    return g


def _sys_cfg(loss_pct: float = 33.0) -> SystemConfig:
    cfg = SystemConfig()
    cfg.daily_loss_pct = loss_pct
    cfg.daily_profit_pct = 0.0
    return cfg


def test_deposit_is_not_counted_as_profit():
    g = _guard()
    g.set_cash_flow(DEPOSIT)

    # Trading truth: (-304.62 + 151.29) / 1723.44 = -8.90%
    # Agrees with the deposit-immune sibling path (_symbol_daily_halt's
    # realised+floating) to within the 2dp rounding of its inputs.
    assert g.pnl_pct(EQUITY) == pytest.approx(
        (REALISED + FLOATING) / START_BALANCE * 100.0, abs=0.01)
    assert round(g.pnl_pct(EQUITY), 2) == -8.90  # live panel read -8.96 later
    assert g.pnl_pct(EQUITY) < 0.0, "a losing day must not report as profit"


def test_without_the_correction_the_day_reads_positive():
    """Pins the exact defect: no cash-flow correction => the +20.11% panel lie."""
    g = _guard()  # cash_flow left at 0.0 - the old behaviour
    assert round(g.pnl_pct(EQUITY), 2) == 20.11


def test_deposit_cannot_hold_the_loss_breaker_open():
    """A deposit must not buy the account more room to lose."""
    equity = START_BALANCE + DEPOSIT - 600.0  # -34.8% of the anchor, past the 33% cap
    g = _guard()
    g.set_cash_flow(DEPOSIT)

    verdict = g.check(equity=equity, sys_cfg=_sys_cfg(33.0))

    assert verdict.ok is False
    assert g.halted is True and g.loss_halted is True


def test_withdrawal_does_not_fake_a_loss():
    """The correction must be symmetric - a withdrawal is not a trading loss."""
    g = _guard()
    g.set_cash_flow(-500.0)

    # Flat trading, 500 withdrawn: equity is down 500 but the day made nothing.
    assert g.pnl_pct(START_BALANCE - 500.0) == 0.0
    assert g.check(START_BALANCE - 500.0, _sys_cfg(3.0)).ok is True


def test_failed_history_read_holds_the_last_known_value():
    """A disconnect must not silently revert the anchor and re-disarm the breaker."""
    g = _guard()
    g.set_cash_flow(DEPOSIT)
    g.set_cash_flow(None)  # mt5client.cash_flow_since() returning None
    assert g.cash_flow == DEPOSIT
    assert g.pnl_pct(EQUITY) < 0.0


def test_cash_flow_survives_restart():
    store = _FakeStore()
    _guard(store).set_cash_flow(DEPOSIT)

    revived = DailyGuard(store)  # same store, fresh process
    assert revived.cash_flow == DEPOSIT


def test_rollover_clears_cash_flow():
    """New anchor, so yesterday's deposit is no longer relative to it."""
    import time as _time

    store = _FakeStore()
    g = _guard(store)
    g.set_cash_flow(DEPOSIT)

    g.rollover(server_epoch=_time.time() + 86400 * 2, balance=2000.0)

    assert g.cash_flow == 0.0
    assert DailyGuard(store).cash_flow == 0.0
