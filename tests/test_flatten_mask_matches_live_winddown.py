"""Paper flatten in the wind-down band is the live should_flatten answer.

flatten_mask claims to mirror should_flatten + day_end_close + weekend_closed.
The in-session wind-down is the shared claim: a bar whose minute is inside
flat_before_close_min of the window end must be True on both sides.

The Friday-to-Monday gap is *not* the same claim. Paper flags Friday's last
bar because no Saturday candle exists; live weekend_closed is false on that
Friday and true on Saturday's clock. Named here so it is not greened away.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.models import SymbolConfig
from micofx.sessions import day_end_close, should_flatten, weekend_closed

# Monday 1970-01-05 / Friday 1970-01-02. Naive broker-wall, same as session_mask.
MON = 4 * 86400
FRI = 1 * 86400


def _cfg() -> SymbolConfig:
    return SymbolConfig(
        symbol="GER40",
        group="index",
        use_sessions=True,
        sessions=[{"start": "03:15", "end": "22:59"}],
        trade_days=[1, 2, 3, 4, 5],
        flat_before_close_min=5,
    )


def _at(day_epoch: int, hour: int, minute: int) -> int:
    return day_epoch + hour * 3600 + minute * 60


def test_winddown_minute_is_a_flatten_on_both_sides():
    cfg = _cfg()
    epoch = _at(MON, 22, 55)
    times = np.array([epoch], dtype=np.int64)
    assert should_flatten(cfg, float(epoch), all_hours=False) is True
    assert bool(backtest.flatten_mask(cfg, times, all_hours=False)[0]) is True


def test_mid_session_is_not_a_flatten_on_either_side():
    cfg = _cfg()
    epoch = _at(MON, 12, 0)
    times = np.array([epoch], dtype=np.int64)
    assert should_flatten(cfg, float(epoch), all_hours=False) is False
    assert bool(backtest.flatten_mask(cfg, times, all_hours=False)[0]) is False


def test_day_end_band_matches_when_the_system_asks_for_it():
    cfg = _cfg()
    epoch = _at(MON, 23, 40)
    times = np.array([epoch], dtype=np.int64)
    assert day_end_close(float(epoch), 30) is True
    assert bool(backtest.flatten_mask(cfg, times, day_end_flatten_min=30)[0]) is True


def test_friday_last_bar_is_paper_weekend_and_not_live_weekend_closed():
    """The gap fill. Live waits for Saturday's clock; paper has no such bar."""
    cfg = _cfg()
    friday_close = _at(FRI, 22, 0)
    monday_open = _at(MON, 3, 15)
    times = np.array([friday_close, monday_open], dtype=np.int64)
    mask = backtest.flatten_mask(cfg, times)
    assert bool(mask[0]) is True
    assert weekend_closed(cfg, float(friday_close)) is False
