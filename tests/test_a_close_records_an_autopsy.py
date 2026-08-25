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
from micofx.engine import TRADE_AUTOPSY_LIMIT, Engine, SymbolState, after_stop_excursions
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
    assert "entry" in row
    assert "sl" in row
    assert "original_sl" in row
    assert "exit_price" in row


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
    assert eng._trade_autopsies[-1]["entry"] == 100.0
    assert eng._trade_autopsies[-1]["sl"] == 99.4
    assert eng._trade_autopsies[-1]["original_sl"] == 99.0
    assert eng._trade_autopsies[-1]["exit_price"] == 99.4


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


def test_the_evaluate_path_fills_after_stop():
    src = inspect.getsource(Engine._evaluate)
    assert "_fill_after_stop" in src, (
        "stop-sonrasi otopsi _evaluate'de yok - yarin yine logdan keseriz"
    )


def test_a_buy_stop_that_comes_back_through_entry_is_a_shakeout():
    out = after_stop_excursions(
        "buy", 100.0, 99.0, 99.0,
        [1000, 1300, 2200, 5000],
        [100.0, 99.2, 101.5, 102.0],
        [99.0, 98.5, 99.1, 99.0],
        exit_time=1000,
    )
    assert out is not None
    assert out["after_1h_bars"] == 2
    assert out["after_1h_extra_r"] == 0.5
    assert out["after_1h_recovery_r"] == 2.5
    assert out["after_1h_through_entry"] is True


def test_a_winning_trail_is_not_a_shakeout_just_because_price_stayed_above_entry():
    """Gold 24.08 14:46: dip 13.75 above entry, through_entry was True anyway."""
    out = after_stop_excursions(
        "buy", 100.0, 99.0, 102.0,
        [1000, 1600, 2800],
        [103.0, 103.5, 102.8],
        [101.5, 101.2, 101.8],
        exit_time=1000,
    )
    assert out is not None
    assert out["after_1h_through_entry"] is False


def test_a_buy_stop_that_keeps_falling_is_continuation():
    out = after_stop_excursions(
        "buy", 100.0, 99.0, 99.0,
        [1000, 1600, 2800],
        [100.0, 98.9, 98.4],
        [99.0, 97.0, 95.2],
        exit_time=1000,
    )
    assert out is not None
    assert out["after_1h_extra_r"] == 3.8
    assert out["after_1h_recovery_r"] == 0.0
    assert out["after_1h_through_entry"] is False


def test_a_sell_stop_recovery_through_entry_is_a_shakeout():
    out = after_stop_excursions(
        "sell", 100.0, 101.0, 101.0,
        [50, 200, 800],
        [100.5, 102.5, 101.2],
        [99.8, 99.0, 99.5],
        exit_time=50,
    )
    assert out is not None
    assert out["after_1h_extra_r"] == 1.5
    assert out["after_1h_recovery_r"] == 2.0
    assert out["after_1h_through_entry"] is True


def test_missing_prices_or_an_empty_window_return_none():
    assert after_stop_excursions(
        "buy", 100.0, 100.0, 99.0, [1], [1], [1], exit_time=0,
    ) is None
    assert after_stop_excursions(
        "buy", 100.0, 99.0, 99.0, [1], [101], [98], exit_time=100,
    ) is None


def test_the_bar_the_stop_landed_on_counts_when_bar_sec_is_known():
    """Open-stamp window dropped gold's 14:45 M15; overlap keeps it."""
    out = after_stop_excursions(
        "buy", 100.0, 99.0, 99.0,
        [1000, 1300, 2200, 5000],
        [100.0, 99.2, 101.5, 102.0],
        [99.0, 98.5, 99.1, 99.0],
        exit_time=1000,
        bar_sec=900,
    )
    assert out is not None
    assert out["after_1h_bars"] == 3


def test_fill_after_stop_waits_until_the_hour_has_closed():
    eng = _engine()
    eng._trade_autopsies = [_priced_row(exit_time=1000)]
    state = SymbolState("GER40")
    state.bars = _bars(last=2000)
    eng._fill_after_stop("GER40", state)
    assert "after_1h_bars" not in eng._trade_autopsies[0]
    assert eng._trade_autopsies_dirty is False


def test_fill_after_stop_uses_the_bar_close_not_its_open_stamp():
    """A bar that opened 97s before the hour elapsed has already closed.

    Gold 24.08 14:46: the 15:45 M15 finished at 16:00; waiting on the open
    stamp pushed the fill to 16:15. Observation only.
    """
    eng = _engine()
    eng.store.symbols["GER40"] = SymbolConfig(symbol="GER40", magic=1, timeframe="M15")
    exit_t = 1000
    last_open = exit_t + 3600 - 97
    eng._trade_autopsies = [_priced_row(exit_time=exit_t)]
    state = SymbolState("GER40")
    state.bars = _bars(last=last_open)
    eng._fill_after_stop("GER40", state)
    assert eng._trade_autopsies[0].get("after_1h_bars") == 4


def test_fill_after_stop_writes_the_hour_once_bars_exist():
    eng = _engine()
    eng._trade_autopsies = [_priced_row(exit_time=1000)]
    state = SymbolState("GER40")
    state.bars = _bars(last=5000)
    eng._fill_after_stop("GER40", state)
    row = eng._trade_autopsies[0]
    assert row["after_1h_bars"] == 3
    assert row["after_1h_through_entry"] is True
    assert row["after_1h_extra_r"] == 0.5
    assert row["after_1h_recovery_r"] == 2.5
    assert eng._trade_autopsies_dirty is True


def test_fill_after_stop_marks_a_row_without_prices_done():
    eng = _engine()
    eng._trade_autopsies = [{"symbol": "GER40", "exit_time": 1000, "side": "buy"}]
    state = SymbolState("GER40")
    state.bars = _bars(last=5000)
    eng._fill_after_stop("GER40", state)
    assert eng._trade_autopsies[0]["after_1h_bars"] == 0


def test_fill_after_stop_does_not_walk_rows_already_filled():
    eng = _engine()
    done = {**_priced_row(exit_time=1), "after_1h_bars": 4, "symbol": "GER40"}
    pending = _priced_row(exit_time=1000)
    eng._trade_autopsies = [done] * 200 + [pending]
    eng._rebuild_autopsy_pending()
    assert len(eng._pending_autopsies("GER40")) == 1
    state = SymbolState("GER40")
    state.bars = _bars(last=5000)
    eng._fill_after_stop("GER40", state)
    assert pending.get("after_1h_bars") is not None
    assert done["after_1h_bars"] == 4
    assert eng._pending_autopsies("GER40") == []


def test_fill_after_stop_does_not_raise_on_broken_bars():
    eng = _engine()
    eng._trade_autopsies = [_priced_row(exit_time=1000)]
    state = SymbolState("GER40")
    state.bars = object()  # type: ignore[assignment]
    eng._fill_after_stop("GER40", state)


def test_the_autopsy_report_counts_after_stop_shakeouts():
    eng = _engine()
    eng._trade_autopsies = [
        {**_priced_row(exit_time=1), "after_1h_bars": 4,
         "after_1h_through_entry": True, "after_1h_extra_r": 0.2,
         "after_1h_recovery_r": 1.1},
        {**_priced_row(exit_time=2), "after_1h_bars": 3,
         "after_1h_through_entry": False, "after_1h_extra_r": 1.4,
         "after_1h_recovery_r": 0.0},
        {**_priced_row(exit_time=3), "after_1h_bars": 0},
    ]
    report = eng.trade_autopsy_report()
    assert report["after_1h_n"] == 2
    assert report["after_1h_through_entry"] == 1
    assert report["after_1h_extra_ge_0_5r"] == 1
    assert report["after_1h_recovery_ge_0_5r"] == 1


def _priced_row(*, exit_time: int) -> dict:
    return {
        "symbol": "GER40", "side": "buy", "ticket": 1,
        "entry": 100.0, "sl": 99.4, "original_sl": 99.0,
        "exit_price": 99.0, "exit_time": exit_time,
    }


class _bars:
    def __init__(self, *, last: int) -> None:
        self.time = [1000, 1300, 2200, last]
        self.high = [100.0, 99.2, 101.5, 102.0]
        self.low = [99.0, 98.5, 99.1, 99.0]

    @property
    def last_closed_time(self) -> int:
        return int(self.time[-1])

