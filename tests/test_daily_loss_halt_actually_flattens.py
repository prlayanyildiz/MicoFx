"""The daily loss limit must close what is open, not just refuse new entries.

Both ends of this are covered and the wire between them was not. ``DailyGuard``
has tests for tripping on the loss side, for staying tripped when equity bounces
back, for not tripping the loss flag on a profit target, and for clearing on
rollover. ``MT5Client.close_all`` has tests for reporting an unknown remainder
when resolve or positions_get fails. The branch in ``_cycle`` that turns the
first into the second had none, and it is the single most consequential path in
the system: the guard alone only ever blocked NEW entries, so an already-open
position kept riding its own possibly-distant stop while the account bled past
the configured limit.

Four properties, all of them decisions someone made on purpose:

  * a loss halt with positions open flattens them;
  * a PROFIT-target halt does not - letting winners run is a legitimate choice
    and the asymmetry is deliberate;
  * it runs every cycle while halted rather than once, so a partial close_all
    is retried instead of leaving the rest open;
  * a close that could not be verified (remaining < 0, meaning disconnect or
    resolve failure rather than "minus one ticket") is reported as unverified,
    not as success.

Written while the live account sat at -11.6% against a 17% limit, which is the
reason it is worth pinning rather than reading.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.risk import DailyGuard

START_BALANCE = 1000.0


class _Store:
    def __init__(self, flatten=True, loss_pct=17.0, profit_pct=0.0):
        self.system = SimpleNamespace(
            slippage_points=5, block_high_cost=False, max_cost_pct_of_risk=0.0,
            trade_all_hours=True, daily_loss_flatten=flatten, day_end_flatten_min=0,
            daily_loss_pct=loss_pct, daily_profit_pct=profit_pct,
            max_total_positions=100, poll_interval_sec=2.0,
        )
        self.symbols = {}
        self.settings = {}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value

    def opt_params(self):
        return {}


class _Thread:
    """``watching`` is a read-only property over the cycle thread, so it is set
    by handing the engine one that reports itself alive."""

    def is_alive(self):
        return True


class _Client:
    """close_all reports ``(closed, remaining)``; remaining < 0 means it could
    not be verified at all."""

    def __init__(self, positions, closed=None, remaining=0):
        self.connected = True
        self._positions = list(positions)
        self._closed = len(positions) if closed is None else closed
        self._remaining = remaining
        self.close_all_calls = 0

    def positions(self, magic=None, symbol=None):
        return list(self._positions)

    def close_all(self, *a, **kw):
        self.close_all_calls += 1
        return self._closed, self._remaining

    def set_overrides(self, m):
        pass

    def ensure(self):
        return True

    def server_now(self):
        return 1_786_000_000.0

    def cash_flow_since(self, ts):
        # No deposits/withdrawals in these scenarios, so the guard's equity
        # anchor is uncorrected and these cases read exactly as before.
        return 0.0

    def account(self):
        return {"balance": START_BALANCE, "equity": self._equity}


def _pos(ticket, symbol="GER40"):
    return {"ticket": ticket, "symbol": symbol, "magic": 1, "volume": 0.1,
            "side": "buy", "profit": -5.0, "swap": 0.0, "sl": 1.0}


def _engine(equity, positions, flatten=True, profit_pct=0.0, remaining=0, closed=None):
    store = _Store(flatten=flatten, profit_pct=profit_pct)
    client = _Client(positions, closed=closed, remaining=remaining)
    client._equity = equity

    eng = object.__new__(Engine)
    eng.store = store
    eng.client = client
    # Both ``running`` and ``watching`` are read-only properties over these.
    eng._trading = True
    eng._thread = _Thread()
    eng._positions = []
    eng._account = {}
    eng._account_at = 0.0
    eng.cycle_count = 0
    eng.last_error = ""

    guard = DailyGuard.__new__(DailyGuard)
    guard.store = store
    guard.day_key = "2026-08-12"
    guard.start_balance = START_BALANCE
    guard.halted = False
    guard.halt_reason = ""
    guard.loss_halted = False
    guard._zero_balance_warned = False
    # No external cash movement in these scenarios; 0.0 leaves the equity
    # anchor uncorrected, so every case below reads exactly as it did before
    # the deposit correction landed.
    guard.cash_flow = 0.0
    eng.risk = SimpleNamespace(daily=guard)

    # Everything _cycle touches on the way to the branch under test, and
    # everything after it. Stubbed on the instance so engine.py is untouched.
    eng.refresh_account = lambda force=False: client.account()
    eng._handle_daily_rollover = lambda *a, **k: False
    eng._reap_execution = lambda *a, **k: None
    eng._apply_pending_exits = lambda *a, **k: None
    eng._scan_orphan_candidates = lambda *a, **k: None
    eng.manage_positions = lambda *a, **k: None
    eng._maybe_schedule_reopt = lambda *a, **k: None
    eng._flush_spread_ratio = lambda *a, **k: None
    eng._save_entry_blocks = lambda *a, **k: None
    eng.supervisor = SimpleNamespace(due=lambda: False, gate=lambda *a, **k: (True, "", 1.0))
    return eng, client, guard


def _run(eng):
    eng._cycle()


# ------------------------------------------------------- the wire under test

def test_a_loss_halt_flattens_open_positions():
    eng, client, guard = _engine(equity=800.0, positions=[_pos(1), _pos(2)])
    _run(eng)
    assert guard.halted is True and guard.loss_halted is True
    assert client.close_all_calls == 1, "gunluk zarar limiti acik pozisyonu kapatmiyor"


def test_it_retries_while_still_halted_rather_than_flattening_once():
    """A partial close leaves positions behind; the next cycle must try again."""
    eng, client, _ = _engine(equity=800.0, positions=[_pos(1)], closed=0, remaining=1)
    _run(eng)
    _run(eng)
    assert client.close_all_calls == 2


def test_an_unverified_close_is_not_treated_as_done():
    """remaining < 0 is "could not check", not "minus one ticket"."""
    eng, client, guard = _engine(equity=800.0, positions=[_pos(1)], closed=0, remaining=-1)
    _run(eng)
    assert client.close_all_calls == 1
    assert guard.loss_halted is True, "dogrulanamayan kapanis halt'i kaldirmamali"


# --------------------------------------------------- the deliberate asymmetry

def test_a_profit_target_halt_does_not_flatten():
    """Letting winners run is a choice; only the loss side flattens."""
    eng, client, guard = _engine(equity=1300.0, positions=[_pos(1)], profit_pct=17.0)
    _run(eng)
    assert guard.halted is True
    assert guard.loss_halted is False
    assert client.close_all_calls == 0


# --------------------------------------------------- what must keep working

def test_an_untroubled_day_does_not_flatten():
    eng, client, guard = _engine(equity=990.0, positions=[_pos(1)])
    _run(eng)
    assert guard.halted is False
    assert client.close_all_calls == 0


def test_the_switch_is_respected():
    eng, client, guard = _engine(equity=800.0, positions=[_pos(1)], flatten=False)
    _run(eng)
    assert guard.loss_halted is True, "halt yine de tripmeli"
    assert client.close_all_calls == 0, "flatten kapaliyken kapatmamali"


def test_a_flat_book_does_not_call_close_all():
    eng, client, guard = _engine(equity=800.0, positions=[])
    _run(eng)
    assert guard.loss_halted is True
    assert client.close_all_calls == 0


def test_the_limit_is_measured_on_equity_not_balance():
    """Floating loss counts. Balance alone would let the account ride well past
    the limit on open positions - which is the state this whole path exists
    for."""
    eng, client, guard = _engine(equity=800.0, positions=[_pos(1)])
    assert client.account()["balance"] == START_BALANCE
    _run(eng)
    assert guard.loss_halted is True
