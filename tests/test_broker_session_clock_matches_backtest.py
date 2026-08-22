"""Live session clock must match backtest: naive broker epoch, gmtime.

Found in BU: ``sessions.server_clock`` used ``localtime(time.time())`` while
``backtest.session_mask`` uses ``times % 86400``. Pepperstone and Turkey are
both UTC+3 today so the two agree by accident; in October the broker drops to
UTC+2 and live would keep Windows +3.

Also: a stale ``broker_now`` (Friday close on Sunday) must not be read as
'now' and must not fall back to the Windows clock.
"""
from __future__ import annotations

import calendar
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import sessions
from micofx.models import SymbolConfig
from micofx.mt5client import DECISION_CLOCK_MAX_AGE_SEC, MT5Client

HOUR = 3600
# Monday 2026-08-17 12:00 UTC.
UTC_NOON = calendar.timegm((2026, 8, 17, 12, 0, 0, 0, 0, 0))
TR = 3 * HOUR
OCT = 2 * HOUR


def _cfg(start="15:00", end="16:00") -> SymbolConfig:
    return SymbolConfig(
        symbol="GER40",
        use_sessions=True,
        sessions=[{"start": start, "end": end}],
        trade_days=[1, 2, 3, 4, 5],
    )


def test_server_clock_matches_backtest_modulo_on_a_naive_stamp():
    """Same number backtest would store on a bar: 15:00 broker -> hour 15."""
    naive = calendar.timegm((2026, 8, 17, 15, 0, 0, 0, 0, 0))
    day, minute = sessions.server_clock(naive)
    assert minute // 60 == 15
    assert (naive % 86400) // 3600 == 15
    assert day == 1  # Monday


def test_today_utc3_old_and_new_agree_on_the_session():
    """True epoch T, Windows UTC+3, broker naive T+3h: same window decision."""
    cfg = _cfg()
    true_epoch = UTC_NOON
    old_as_local = true_epoch + TR          # what localtime(T) shows in TR
    new_broker = true_epoch + TR            # broker wall encoded as UTC
    assert sessions.evaluate(cfg, old_as_local).open is True
    assert sessions.evaluate(cfg, new_broker).open is True
    assert sessions.server_clock(old_as_local) == sessions.server_clock(new_broker)


def test_october_utc2_moves_the_window_off_windows_local():
    """Broker UTC+2, Windows still UTC+3: new clock follows the broker."""
    cfg = _cfg()
    true_epoch = UTC_NOON
    windows_local = true_epoch + TR         # 15:00 TR, old live
    broker_oct = true_epoch + OCT           # 14:00 broker
    assert sessions.evaluate(cfg, windows_local).open is True
    assert sessions.evaluate(cfg, broker_oct).open is False
    assert sessions.server_clock(broker_oct)[1] // 60 == 14


def test_decision_now_is_none_when_the_stamp_is_stale():
    c = MT5Client.__new__(MT5Client)
    c._broker_now = UTC_NOON
    c._broker_seen_at = time.time() - (DECISION_CLOCK_MAX_AGE_SEC + 60)
    # This test is about staleness, so it starts from a client whose clock
    # has already been watched keeping pace; seeding alone proves nothing.
    c._broker_anchor = (time.time() - 3600.0, UTC_NOON - 3600.0)
    assert c.decision_now() is None


def test_decision_now_returns_the_stamp_when_fresh():
    c = MT5Client.__new__(MT5Client)
    c._broker_now = UTC_NOON + TR
    c._broker_seen_at = time.time()
    c._broker_anchor = (time.time() - 3600.0, UTC_NOON + TR - 3600.0)
    assert c.decision_now() == pytest.approx(UTC_NOON + TR)
