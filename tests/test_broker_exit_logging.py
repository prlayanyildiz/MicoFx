"""A hard stop firing at the broker must leave a line in the log.

The stop is this system's only intended exit, yet it fires with nothing of ours
running - so before this, the normal way a trade ends was the single event the
log never mentioned, and an operator reading the log saw positions simply
vanish between the entry line and the next one.
"""
from __future__ import annotations

import MetaTrader5 as mt5
import pytest

from micofx.execution import DEAL_REASON_SL, DEAL_REASON_SO, ExecutionMonitor


class _Store:
    def __init__(self) -> None:
        self._settings: dict[str, object] = {}

    def get_setting(self, key, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key, value):
        self._settings[key] = value


class _Client:
    def info(self, symbol):
        return {"point": 0.1}

    def money_per_price_unit(self, symbol, volume):
        return 1.0


def _monitor() -> ExecutionMonitor:
    return ExecutionMonitor(_Store())


def _position(ticket=1, symbol="NAS100", side="buy", sl=29725.2, price_open=29778.6,
              magic=7):
    return {"ticket": ticket, "symbol": symbol, "side": side, "sl": sl, "tp": 0.0,
            "price_open": price_open, "magic": magic}


def _deal(position=1, reason=DEAL_REASON_SL, profit=-13.0, commission=0.0, swap=0.0,
          price=29725.0, volume=0.3, entry=None, symbol="NAS100", magic=7):
    return {"position": position, "symbol": symbol, "magic": magic, "volume": volume,
            "price": price, "profit": profit, "commission": commission, "swap": swap,
            "time": 100, "reason": reason,
            "entry": mt5.DEAL_ENTRY_OUT if entry is None else entry, "ticket": 900}


def test_stop_exit_is_reported():
    mon = _monitor()
    mon.track([_position()])
    gone = mon.track([])
    assert gone == {1}

    reports = mon.reap(gone, [_deal()], _Client())
    assert len(reports) == 1
    assert reports[0]["symbol"] == "NAS100"
    assert reports[0]["magic"] == 7
    assert reports[0]["label"] == "stop"
    assert reports[0]["profit"] == -13.0


def test_report_nets_commission_and_swap_across_both_legs():
    # Realised P/L is the whole round trip - a broker charging commission on the
    # entry leg would otherwise be reported as a better trade than it was.
    mon = _monitor()
    mon.track([_position()])
    gone = mon.track([])
    deals = [
        _deal(profit=0.0, commission=-0.5, entry=mt5.DEAL_ENTRY_IN, reason=3),
        _deal(profit=-13.0, commission=-0.5, swap=-0.2),
    ]
    reports = mon.reap(gone, deals, _Client())
    assert reports[0]["profit"] == -14.2


def test_engine_initiated_close_is_not_reported():
    # The engine logs its own closes when it sends them; a deal whose reason is
    # not a broker-side one must not produce a second line for the same exit.
    mon = _monitor()
    mon.track([_position()])
    gone = mon.track([])
    assert mon.reap(gone, [_deal(reason=3)], _Client()) == []


def test_margin_stop_out_is_reported_but_not_scored_as_slippage():
    mon = _monitor()
    mon.track([_position()])
    gone = mon.track([])
    reports = mon.reap(gone, [_deal(reason=DEAL_REASON_SO)], _Client())
    assert len(reports) == 1
    assert reports[0]["reason"] == DEAL_REASON_SO
    # No requested price of ours to compare a margin close against.
    assert mon.stats()["total"]["samples"] == 0


def test_exit_without_remembered_book_still_reported():
    # Restart mid-trade: _open was never populated for this ticket, but the
    # operator still needs to know the position is gone.
    mon = _monitor()
    mon._open[1] = {}
    mon._open[1] = {"symbol": "", "side": "buy", "sl": 0.0, "tp": 0.0,
                    "entry": 0.0, "magic": 7}
    gone = mon.track([])
    reports = mon.reap(gone, [_deal()], _Client())
    assert len(reports) == 1
    assert reports[0]["symbol"] == "NAS100"  # fell back to the deal's symbol


def test_a_stop_filled_in_chunks_reports_the_whole_position():
    # A broker stop can fill in pieces. Keeping only the last closing deal put
    # a fraction of the lot next to a P/L covering the whole position - a line
    # that contradicts itself. Volume sums; price is volume-weighted.
    mon = _monitor()
    mon.track([_position(price_open=29778.6)])
    gone = mon.track([])
    deals = [
        _deal(profit=-8.0, price=29726.0, volume=0.2),
        _deal(profit=-5.0, price=29724.0, volume=0.1),
    ]
    reports = mon.reap(gone, deals, _Client())
    assert len(reports) == 1
    assert reports[0]["volume"] == pytest.approx(0.3)
    assert reports[0]["profit"] == pytest.approx(-13.0)
    # (29726*0.2 + 29724*0.1) / 0.3
    assert reports[0]["price"] == pytest.approx(29725.3333, abs=1e-3)


def test_a_single_fill_price_is_unchanged_by_the_weighting():
    mon = _monitor()
    mon.track([_position()])
    gone = mon.track([])
    reports = mon.reap(gone, [_deal(price=29725.0, volume=0.3)], _Client())
    assert reports[0]["price"] == 29725.0
    assert reports[0]["volume"] == 0.3


def test_target_exit_still_scores_slippage():
    mon = _monitor()
    mon.track([_position(sl=29725.2)])
    gone = mon.track([])
    mon.reap(gone, [_deal(reason=DEAL_REASON_SL, price=29720.0)], _Client())
    stats = mon.stats()
    assert stats["total"]["samples"] == 1
    assert stats["per_symbol"]["NAS100"]["legs"] == {"stop": 1}
