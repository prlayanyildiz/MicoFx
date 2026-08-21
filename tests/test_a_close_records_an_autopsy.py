"""POST-1: every close must leave an autopsy row.

The operator's questions (why little profit, why a loss, was the fill on time)
were answered from one-off scripts. A close that only logs ``kar=`` cannot
feed the next measurement. The ring is a bounded store, not a gate: nothing
here changes entries or exits.
"""
from __future__ import annotations

import inspect
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_a_hand_closed_position_is_reported import BOOK, _Client, _deal, _tracker

from micofx import execution
from micofx.engine import TRADE_AUTOPSY_LIMIT, Engine
from micofx.models import SymbolConfig


def test_the_broker_exit_path_records_an_autopsy():
    src = inspect.getsource(Engine._log_broker_exit)
    assert "_autopsy_safe" in src, (
        "broker kapanisi otopsi yazmiyor - yarin yine elle betik kosariz"
    )


def test_the_engine_close_path_records_an_autopsy():
    src = inspect.getsource(Engine._close_tracked)
    assert "_autopsy_safe" in src, (
        "motorun kendi kapanisi otopsi yazmiyor (flatten/hafta sonu)"
    )


def test_a_broken_autopsy_cannot_break_the_close():
    """The property that matters more than the row itself.

    Both call sites sit in the bookkeeping that runs after the position is
    already gone at the broker, and one of them is inside ``_close_tracked``
    after a successful close - an exception there would reach the caller as a
    failed close that in fact happened. So the recorder is called through a
    guard, and this is the test for the guard rather than for the name.
    """
    eng = _engine()

    def explode(**_kw):
        raise ValueError("bozuk satir")

    eng._autopsy_row = explode                     # type: ignore[method-assign]
    eng._autopsy_safe(book={}, ticket=1, symbol="GER40", exit_price=1.0,
                      exit_time=0, profit=None, reason_code=None, comment="")
    assert eng._trade_autopsies == [], "bozuk satir halkaya girdi"


def test_a_row_with_missing_fields_is_still_kept():
    """A close with no ticket still carries its excursions; keep the row."""
    eng = _engine()
    eng._autopsy_safe(book={"side": "buy", "entry": 100.0, "risk_dist": 2.0,
                            "mfe": 3.0, "mae": 1.0},
                      ticket=None, symbol=None, exit_price=101.0,
                      exit_time=None, profit=None, reason_code=None, comment="")
    assert len(eng._trade_autopsies) == 1
    row = eng._trade_autopsies[0]
    assert row["ticket"] == 0 and row["mfe_r"] == 1.5


def _engine() -> Engine:
    eng = Engine.__new__(Engine)
    cfg = SymbolConfig(symbol="GER40", magic=1)

    class Store:
        def __init__(self):
            self.symbols = {cfg.symbol: cfg}
            self.settings = {}

        def get_setting(self, key, default=None):
            return self.settings.get(key, default)

        def set_setting(self, key, value):
            self.settings[key] = value

    eng.store = Store()
    eng._trade_autopsies = []
    eng._trade_autopsies_dirty = False
    eng._trade_autopsy_limit = TRADE_AUTOPSY_LIMIT
    eng._flush_ok = lambda *_a, **_k: None
    eng._flush_failed = lambda *_a, **_k: None
    return eng


def test_a_broker_stop_appends_an_autopsy_row():
    eng = _engine()
    tracker = _tracker(BOOK)
    reports = tracker.reap(
        gone={7}, deals=[_deal(7, execution.DEAL_REASON_SL)], client=_Client())
    assert reports, "reap bos dondu"
    eng._log_broker_exit(reports[0])
    assert eng._trade_autopsies, "kapanis otopsi birakmadi"
    row = eng._trade_autopsies[-1]
    assert row["symbol"] == "GER40"
    assert row["exit_reason"] in {"sl", "trail"}
    assert "r_realised" in row
    assert "mfe_r" in row
    assert "left_on_table_r" in row


def test_the_autopsy_ring_drops_the_oldest_past_the_cap():
    eng = _engine()
    eng._trade_autopsy_limit = 3
    for i in range(5):
        eng.record_trade_autopsy({"symbol": "GER40", "ticket": i, "exit_reason": "sl"})
    assert [r["ticket"] for r in eng._trade_autopsies] == [2, 3, 4]
    assert len(eng._trade_autopsies) == 3


def test_open_book_accumulates_mfe_and_mae_in_price():
    """Peak excursion is from entry, frozen risk_dist is first-sight stop.

    A later trail must not shrink the R the close will divide by, and a
    retrace after a peak must not forget the peak.
    """
    tracker = _tracker()
    tracker.track([{
        "ticket": 1, "symbol": "GER40", "side": "buy", "sl": 99.0, "tp": 0.0,
        "price_open": 100.0, "price_current": 101.0, "magic": 1, "time": 10,
    }])
    tracker.track([{
        "ticket": 1, "symbol": "GER40", "side": "buy", "sl": 99.5, "tp": 0.0,
        "price_open": 100.0, "price_current": 99.5, "magic": 1, "time": 10,
    }])
    book = tracker._open[1]
    assert book["mfe"] == 1.0
    assert book["mae"] == 0.5
    assert book["risk_dist"] == 1.0
    assert book["original_sl"] == 99.0


def test_a_moved_stop_is_labelled_trail_not_sl():
    eng = _engine()
    eng.record_trade_autopsy(eng._autopsy_row(
        book={"entry": 100.0, "side": "buy", "risk_dist": 1.0,
              "original_sl": 99.0, "sl": 99.4, "mfe": 0.8, "mae": 0.2},
        ticket=8, symbol="GER40", exit_price=99.4, exit_time=100,
        profit=-1.0, reason_code=execution.DEAL_REASON_SL, comment="",
    ))
    assert eng._trade_autopsies[-1]["exit_reason"] == "trail"
    assert eng._trade_autopsies[-1]["left_on_table_r"] == 1.4


def test_the_autopsy_report_is_on_the_panel():
    src = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py").read_text(
        encoding="utf-8")
    assert "/api/analysis/trade-autopsies" in src
    assert "trade_autopsy_report" in src


def test_autopsy_since_is_the_oldest_row_not_a_stamp_from_before_the_table():
    """19.08 09:43 stamp survived restarts; first row landed 15:19.

    Completeness vs broker closes used the stamp and counted four SL exits
    the ring never contained. The window is the rows.
    """
    eng = _engine()
    eng.store.settings["trade_autopsies_since"] = 1000.0
    eng.store.settings["trade_autopsies"] = [
        {"symbol": "GER40", "ticket": 1, "exit_time": 5000},
        {"symbol": "NAS100", "ticket": 2, "exit_time": 8000},
    ]
    eng._load_trade_autopsies()
    assert eng._trade_autopsies_since == 5000
    assert eng.trade_autopsy_report()["since"] == 5000


def test_an_empty_autopsy_ring_does_not_restore_a_since_that_covers_nothing():
    eng = _engine()
    eng.store.settings["trade_autopsies_since"] = 1000.0
    eng.store.settings["trade_autopsies"] = []
    before = time.time()
    eng._load_trade_autopsies()
    assert eng._trade_autopsies_since >= before
    assert eng._trade_autopsies_since != 1000.0


def test_flush_persists_the_row_derived_since():
    eng = _engine()
    eng._trade_autopsies_since = 1000.0
    eng.record_trade_autopsy({"symbol": "GER40", "ticket": 1, "exit_time": 5000})
    eng._flush_trade_autopsies()
    assert eng.store.settings["trade_autopsies_since"] == 5000

