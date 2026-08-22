"""A stale first tick is not evidence that the broker clock just moved.

MetaTrader5's Python API has no TimeCurrent(), so the newest tick stamp is the
only broker clock available and it stands still while the market is shut. The
staleness guard exists to keep that frozen stamp out of the skew warning - but
it measured how long this process had been watching rather than how old the
stamp was, and a fresh process starts with nothing to compare against. So the
first tick, however old, counted as an advance and stamped the age at zero.

Restarting on a closed market on 22.08 put "broker saati yerel saatten -8 saat
farkli" in the live log, which is the reading the guard was written to prevent.
Until an advance is actually observed, the age is unknowable, and unknowable
answers None.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.mt5client import MT5Client


def _client() -> MT5Client:
    c = object.__new__(MT5Client)
    c._broker_now = 0.0
    c._broker_seen_at = 0.0
    c._broker_advanced = False
    return c


def _observe(c: MT5Client, stamp: float) -> None:
    """The advance bookkeeping from tick(), without the terminal."""
    if stamp > c._broker_now:
        if c._broker_now > 0.0:
            c._broker_advanced = True
        c._broker_now = stamp
        c._broker_seen_at = time.time()


def test_age_is_unknown_before_any_tick():
    assert _client().broker_now_age() is None


def test_the_seeding_tick_does_not_make_a_stale_clock_look_fresh():
    c = _client()
    friday_close = time.time() - 8 * 3600
    _observe(c, friday_close)

    assert c.broker_now() == friday_close, "saat yine de okunur"
    assert c.broker_now_age() is None, (
        "ilk okuma saatin ilerledigini gostermez - bayat damga taze sayilmamali")


def test_a_real_advance_makes_the_age_measurable_again():
    c = _client()
    _observe(c, time.time() - 8 * 3600)
    _observe(c, time.time() - 8 * 3600 + 60)      # ticks start flowing

    age = c.broker_now_age()
    assert age is not None and age < 5.0, "gercek ilerleme olcumu geri acar"


def test_a_stamp_that_does_not_move_never_counts_as_an_advance():
    c = _client()
    stamp = time.time() - 40 * 3600
    _observe(c, stamp)
    for _ in range(5):
        _observe(c, stamp)                        # shut market, same stamp
    assert c.broker_now_age() is None


def test_a_weekend_restart_no_longer_hands_friday_to_the_money_gate():
    """The last-mile weekend guard consumed a stamp it believed was current.

    _try_entry calls decision_now() immediately before spending money,
    precisely so it does not take the session gate's word for the weekend. On
    a restart with the market shut, decision_now() answered with Friday's
    close - fresh, by a staleness test that could not tell a seeding read from
    an advance - and sessions.weekend_closed() was then asked about a Friday.
    It said no.

    Measured on the live database at 08:20 on Saturday 22.08, after a restart
    at 08:18: the guard returned False for the stale stamp and True for the
    real time. Fail-closed means None here, which the entry path already turns
    into "broker saati bayat" and refuses.
    """
    friday_close = time.time() - 8 * 3600
    c = _client()
    _observe(c, friday_close)
    assert c.decision_now() is None, "bayat damga karar saati olarak verilmemeli"

    # Once ticks really flow again, the gate gets its clock back.
    _observe(c, friday_close + 60)
    assert c.decision_now() is not None
