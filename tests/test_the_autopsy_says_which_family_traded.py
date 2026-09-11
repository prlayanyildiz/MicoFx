"""427 trades of live record and no way to ask which strategy lost the money.

Operator, 11.09: "3 koldan stratejilere bakin". The first arm ran into a wall
immediately. The autopsy row carried the symbol and not the family, and a
symbol's family changes under it - US30 went mtf_pullback -> keltner_break at
23:41 on 11.09 - so a row from last week describes a configuration that no
longer exists. Every conclusion of the form "family X loses money" was
unreachable from the live record.

It has to be stamped at FILL, not read from the config at close: by the time a
trade closes the symbol may already carry a different family, which is exactly
the case that makes the stamp necessary.

The history before this is not recoverable. What it buys is that the same
question is answerable in a few days instead of never.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


def test_the_fill_stamps_the_family_and_the_bar():
    """Both open paths - the direct fill and the verified one - carry it."""
    src = inspect.getsource(Engine)
    assert src.count('strategy=str(cfg.strategy or "")') == 2, (
        "note_fill must stamp the family on BOTH open paths "
        "(direct fill and pending-verify)")
    assert src.count('timeframe=str(cfg.timeframe or "")') == 2


def test_the_autopsy_row_reads_them_from_the_book_not_the_config():
    """Reading cfg at close time would record the family the symbol has NOW,
    which is the bug this is here to prevent."""
    src = inspect.getsource(Engine._autopsy_row) if hasattr(
        Engine, "_autopsy_row") else inspect.getsource(Engine)
    assert '"strategy": str(book.get("strategy") or "") or None' in src
    assert '"timeframe": str(book.get("timeframe") or "") or None' in src
    assert '"strategy": str(cfg.strategy' not in src, \
        "family read from the live config at close - it may have changed"


def test_note_fill_keeps_what_the_fill_said():
    """execution.note_fill setdefaults, so a later track() cannot overwrite
    the family with anything. Pinned because the whole point is that the
    stamp survives a config change mid-trade."""
    from micofx.execution import ExecutionMonitor

    src = inspect.getsource(ExecutionMonitor.note_fill)
    assert "book.setdefault(key, value)" in src, (
        "note_fill no longer setdefaults - a later write could overwrite the "
        "family stamp")


def test_the_bad_hour_bar_is_reachable_by_this_book():
    """Third stored value found disabling a mechanism outright.

    `bad_hour_min_trades` held 80 against a shipped default of 6, and
    `Supervisor._bad_hours` buckets PER SYMBOL: 32-98 trades over 30 days
    across 24 hours is two to six per bucket. The blocker could not fire at
    any volume this book will see, while UTC 3/11/12/13/16 carried -60.78R -
    77% of the entire loss on 27% of the trades.

    The bar stays a bar (floor 3), it just has to be reachable.
    """
    from micofx.supervisor import DEFAULTS
    from micofx.web.app import _AI_BOUNDS, _OPERATOR_AI_FIELDS

    assert "bad_hour_min_trades" in _OPERATOR_AI_FIELDS
    low, high, _ = _AI_BOUNDS["bad_hour_min_trades"]
    assert low >= 3, "one or two trades is noise, not an hour verdict"
    shipped = int(DEFAULTS["bad_hour_min_trades"])
    assert low <= shipped <= high, (
        f"shipped default {shipped} is outside the writable range")
    # A book of four symbols over the supervisor's own 30-day lookback puts a
    # few trades in each hour bucket. Anything near a hundred is a switch-off
    # dressed as a threshold.
    assert shipped <= 25, (
        f"shipped bad_hour_min_trades={shipped} cannot be reached per symbol "
        f"per hour on a four-symbol book")


# ------------------------------ why the family stamp was not enough on its own

def test_the_entry_context_is_recorded_too():
    """The three features the autopsy held could not tell a dead signal from
    a working one.

    Measured 11.09, within each symbol, dead (MFE below its own lock
    threshold) against working:

        GER40   atr_pct -10%   spread_atr +28% (the WRONG way)   adx n/a
        NAS100  atr_pct  +9%   spread_atr  -5%
        XAUUSD  atr_pct  -7%   spread_atr +13%   adx +6%

    Nothing separates. The pooled result that looked like a separator was a
    composition effect across symbols with different costs. So "why do 57% of
    entries go nowhere" was unanswerable from the record - the record held
    three numbers, and the strategies decide on more than three.

    entry_context stamps what they actually decide on: higher-timeframe state,
    trend direction against the side taken, the stochastic pair, where the
    fill sits in the recent range, the session and the gap since the last
    signal. All of it is on the symbol state already or one subtraction away.
    """
    src = inspect.getsource(Engine)
    assert src.count("**entry_context(state, side, fill_px)") == 2, (
        "entry context must be stamped on BOTH open paths")
    for key in ("htf", "t3_rising", "with_trend", "stoch_k", "range_pos",
                "session_at_fill", "since_last_signal_sec"):
        assert f'"{key}": book.get("{key}")' in src, f"{key} not in the autopsy row"


def test_entry_context_never_costs_a_fill_its_row():
    """A missing attribute on the state must not raise into the fill path."""
    from micofx.engine import entry_context

    class _Bare:
        pass

    assert entry_context(_Bare(), "buy", 100.0) == {} or isinstance(
        entry_context(_Bare(), "buy", 100.0), dict)
    assert isinstance(entry_context(None, "", 0.0), dict)


def test_range_pos_says_where_in_the_range_the_fill_landed():
    """Buying the top of a range is how a breakout becomes a dead trade, and
    nothing in the old record could show it."""
    import numpy as np

    from micofx.bars import Bars
    from micofx.engine import entry_context

    n = 60
    rates = np.zeros(n, dtype=[("time", np.int64), ("open", np.float64),
                               ("high", np.float64), ("low", np.float64),
                               ("close", np.float64), ("spread", np.float64),
                               ("tick_volume", np.float64)])
    rates["high"] = 110.0
    rates["low"] = 100.0
    rates["close"] = 105.0

    class _State:
        bars = Bars(rates, 0)
        htf = "up"
        t3_rising = True
        k = 80.0
        d = 70.0
        session = "london"
        signal_source = "primary"
        last_signal_at = 0.0

    top = entry_context(_State(), "buy", 110.0)
    mid = entry_context(_State(), "buy", 105.0)
    bottom = entry_context(_State(), "sell", 100.0)
    assert top["range_pos"] == 1.0
    assert mid["range_pos"] == 0.5
    assert bottom["range_pos"] == 0.0
    assert top["with_trend"] is True, "rising t3 + buy is with the trend"
    assert bottom["with_trend"] is False, "rising t3 + sell is against it"
