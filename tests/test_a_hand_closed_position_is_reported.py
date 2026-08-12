"""Closing a position by hand must leave a line, not a silence.

The exit reporter accepted three MT5 deal reasons - SL, TP and the broker's
margin stop-out. Those are the server closing a position on its own. A human
closing one from the terminal, the phone or the web client carries a different
reason, and none of them were in the filter: the deal list held no matching
chunk, the loop hit ``continue``, and the position simply stopped being tracked
with nothing written down.

Found by a count that would not reconcile. For 12 August the panel reported
thirty-four closed trades and the log held twenty-nine "Stop ile kapandi" lines.
Log rotation was the obvious suspect and was wrong - the file was 1.1 MB against
a 4 MB limit and had never rotated. The five were closes made by hand, and every
loss attribution built off that log was short by exactly them, silently: the
day's realised total, the per-symbol shares, all of it.

EXPERT stays out of the filter deliberately. That reason covers this engine's
own close_all and panel routes, which already report; a foreign EA's deals are
dropped by the magic filter in _log_broker_exit regardless.

Bookkeeping was never the problem - ``self._open.pop`` runs before the filter,
so a hand-closed ticket was always released correctly. What was missing was the
record.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import execution
from micofx.execution import ExecutionMonitor


class _Client:
    def info(self, symbol):
        return {"point": 0.01, "tick_size": 0.01, "tick_value": 0.01}

    def money_per_price_unit(self, symbol, volume):
        return float(volume)


def _tracker(book=None) -> ExecutionMonitor:
    t = ExecutionMonitor.__new__(ExecutionMonitor)
    t._open = dict(book or {})
    # Mirrors __init__ without touching the store: reap()'s scoring path
    # writes through _samples/_dirty on the way past.
    t.store = None
    t._samples = {}
    t._dirty = False
    return t


def _deal(ticket, reason, profit=-5.0, volume=0.1, price=100.0, symbol="GER40"):
    return {"position": ticket, "ticket": ticket * 10, "reason": reason,
            "symbol": symbol, "magic": 1, "volume": volume, "price": price,
            "profit": profit, "commission": 0.0, "swap": 0.0}


BOOK = {7: {"symbol": "GER40", "magic": 1, "sl": 0.0, "tp": 0.0,
            "side": "buy", "volume": 0.1}}


def _reports(reason):
    t = _tracker(BOOK)
    return t.reap(gone={7}, deals=[_deal(7, reason)], client=_Client())


# ------------------------------------------------------------- the defect

def test_a_terminal_close_is_reported():
    reports = _reports(execution.DEAL_REASON_CLIENT)
    assert len(reports) == 1, "elle kapatilan pozisyon hicbir iz birakmiyor"
    assert reports[0]["label"] == "elle (terminal)"
    assert reports[0]["profit"] == -5.0


def test_a_mobile_close_is_reported():
    assert _reports(execution.DEAL_REASON_MOBILE)[0]["label"] == "elle (mobil)"


def test_a_web_close_is_reported():
    assert _reports(execution.DEAL_REASON_WEB)[0]["label"] == "elle (web)"


def test_the_engines_own_closes_stay_out():
    """EXPERT is close_all and the panel routes, which already report - adding
    it here would report the same close twice."""
    assert _reports(3) == []


# --------------------------------------------------- what must keep working

def test_a_stop_is_still_reported_as_a_stop():
    r = _reports(execution.DEAL_REASON_SL)[0]
    assert r["label"] == "stop"


def test_a_target_and_a_margin_stopout_are_unchanged():
    assert _reports(execution.DEAL_REASON_TP)[0]["label"] == "hedef"
    assert _reports(execution.DEAL_REASON_SO)[0]["label"] == "broker marj kapatmasi"


def test_the_ticket_is_released_either_way():
    """Bookkeeping was never the defect: the pop runs before the filter, so a
    hand-closed ticket was always let go. Pinned so a fix here cannot leak it."""
    for reason in (execution.DEAL_REASON_CLIENT, 3, execution.DEAL_REASON_SL):
        t = _tracker(BOOK)
        t.reap(gone={7}, deals=[_deal(7, reason)], client=_Client())
        assert 7 not in t._open, f"reason={reason} bileti birakmadi"


def test_net_includes_commission_and_swap_on_a_hand_close():
    """The whole round trip, same as any other exit - a hand close is not a
    second-class record."""
    t = _tracker(BOOK)
    deal = _deal(7, execution.DEAL_REASON_CLIENT, profit=-5.0)
    deal["commission"] = -1.0
    deal["swap"] = -0.5
    assert t.reap(gone={7}, deals=[deal], client=_Client())[0]["profit"] == -6.5

# ------------------------------------- reported is wider than measured

def test_a_hand_close_is_reported_but_never_scored():
    """The boundary the widened filter must not move. A slippage sample needs a
    requested price to compare the fill against, and a hand close has none -
    scoring it would put a meaningless number into the execution statistics
    that decide whether fills are getting worse.
    """
    t = _tracker({7: {"symbol": "GER40", "magic": 1, "sl": 99.0, "tp": 0.0,
                      "side": "buy", "volume": 0.1}})
    reports = t.reap(gone={7}, deals=[_deal(7, execution.DEAL_REASON_CLIENT)],
                     client=_Client())
    assert len(reports) == 1, "elle kapanis raporlanmali"
    assert not any(t._samples.values()), "elle kapanis kayma ornegi uretmemeli"


def test_a_broker_stop_is_still_scored():
    """The other side of the same boundary - remove this and the widened filter
    could quietly stop measuring anything."""
    t = _tracker({7: {"symbol": "GER40", "magic": 1, "sl": 99.0, "tp": 0.0,
                      "side": "buy", "volume": 0.1}})
    t.reap(gone={7}, deals=[_deal(7, execution.DEAL_REASON_SL, price=98.5)],
           client=_Client())
    assert any(t._samples.values()), "broker stopu hala olculmeli"


def test_a_margin_stopout_is_reported_but_not_scored():
    """Documented already: a margin stop-out has no requested price of ours."""
    t = _tracker({7: {"symbol": "GER40", "magic": 1, "sl": 99.0, "tp": 0.0,
                      "side": "buy", "volume": 0.1}})
    reports = t.reap(gone={7}, deals=[_deal(7, execution.DEAL_REASON_SO)],
                     client=_Client())
    assert len(reports) == 1
    assert not any(t._samples.values())
