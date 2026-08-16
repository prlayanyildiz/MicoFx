"""Daily chip must belong to a login. Switching accounts is not a loss.

Live 16.08: demo chip 2113.60 on 61562752, terminal then on another
account at 0.51. DailyGuard treated the gap as trading, wrote
\"Gunluk zarar limiti asildi (-99.98%)\" and locked the day to disk.

The chip is persisted with the account number. A different login rebuilds
the chip at the new balance; the gap is not P&L and must not halt.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SystemConfig
from micofx.risk import DailyGuard

DAY = 1_700_000_000.0

# Live figures, 16.08.2026.
DEMO_LOGIN = 61562752
DEMO_CHIP = 2113.60
OTHER_LOGIN = 51501624
OTHER_BALANCE = 0.51


class _FakeStore:
    def __init__(self) -> None:
        self.data: dict = {}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _guard(store=None) -> DailyGuard:
    return DailyGuard(store or _FakeStore())


def _sys_cfg(loss_pct: float = 3.0) -> SystemConfig:
    cfg = SystemConfig()
    cfg.daily_loss_pct = loss_pct
    cfg.daily_profit_pct = 0.0
    return cfg


def test_switching_account_does_not_count_the_balance_gap_as_a_loss():
    """The 16.08 incident: 2113.60 chip vs 0.51 on another login is not -99.98%."""
    g = _guard()
    g.rollover(DAY, DEMO_CHIP, login=DEMO_LOGIN)
    assert g.start_login == DEMO_LOGIN

    verdict = g.check(OTHER_BALANCE, _sys_cfg(), login=OTHER_LOGIN, balance=OTHER_BALANCE)

    assert verdict.ok is True, verdict.reason
    assert not g.halted and not g.loss_halted
    assert g.start_balance == OTHER_BALANCE
    assert g.start_login == OTHER_LOGIN
    assert "99.98" not in (g.halt_reason or "")


def test_a_false_halt_already_on_disk_clears_when_the_account_changes():
    """The incident wrote the halt. Next cycle must not keep it."""
    store = _FakeStore()
    g = _guard(store)
    g.rollover(DAY, DEMO_CHIP, login=DEMO_LOGIN)
    # Reproduce what the old check() persisted.
    g._halt("Gunluk zarar limiti asildi (-99.98%). Yeni islem yok.", loss=True)
    assert g.halted and g.loss_halted

    rebuilt = g.rollover(DAY, OTHER_BALANCE, login=OTHER_LOGIN)
    assert rebuilt is True
    assert not g.halted and not g.loss_halted
    assert g.start_balance == OTHER_BALANCE
    assert g.start_login == OTHER_LOGIN

    revived = DailyGuard(store)
    assert revived.start_login == OTHER_LOGIN
    assert revived.start_balance == OTHER_BALANCE
    assert not revived.halted


def test_same_account_loss_still_trips_the_breaker():
    g = _guard()
    g.rollover(DAY, DEMO_CHIP, login=DEMO_LOGIN)
    verdict = g.check(DEMO_CHIP * 0.90, _sys_cfg(3.0), login=DEMO_LOGIN, balance=DEMO_CHIP * 0.90)
    assert verdict.ok is False
    assert g.loss_halted


def test_the_login_survives_restart():
    store = _FakeStore()
    g = _guard(store)
    g.rollover(DAY, DEMO_CHIP, login=DEMO_LOGIN)
    revived = DailyGuard(store)
    assert revived.start_login == DEMO_LOGIN
    assert revived.start_balance == DEMO_CHIP


def test_the_cycle_passes_login_into_the_daily_chip():
    """Without this wire the unit tests can pass and live still trips."""
    src = Path("micofx/engine.py").read_text(encoding="utf-8")
    body = src.split("def _cycle(", 1)[1].split("\n    def ", 1)[0]
    assert 'account.get("login"' in body
    rollover_idx = body.index("_handle_daily_rollover")
    check_idx = body.index("self.risk.daily.check")
    assert rollover_idx < check_idx
    # login must reach both the chip rebuild and the halt check
    assert "login=" in body[rollover_idx:rollover_idx + 200]
    assert "login=" in body[check_idx:check_idx + 250]
