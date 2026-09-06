"""Session windows may restrict to specific weekdays (operator hours).

Operator 06.09: SpotBrent Monday opens 01:00 but Tue–Thu 03:00; Friday ends
23:55 while Mon–Thu end 23:59. A single start/end for all trade_days cannot
express that — optional ``days`` on each window can.
"""
from __future__ import annotations

from micofx.models import SymbolConfig
from micofx.sessions import evaluate


def _epoch_for(day: int, hh: int, mm: int) -> float:
    # 1970-01-05 = Monday (day=1). day 1..7 → offset day-1.
    return float((4 + (day - 1)) * 86400 + hh * 3600 + mm * 60)


def test_session_window_days_gate_by_weekday():
    cfg = SymbolConfig(
        symbol="SpotBrent",
        use_sessions=True,
        trade_days=[1, 2, 3, 4, 5],
        sessions=[
            {"start": "01:00", "end": "23:59", "days": [1]},
            {"start": "03:00", "end": "23:59", "days": [2, 3, 4]},
            {"start": "03:00", "end": "23:55", "days": [5]},
        ],
    )
    # Monday 02:00 inside Mon window
    assert evaluate(cfg, _epoch_for(1, 2, 0)).open is True
    # Tuesday 02:00 outside Tue window (starts 03:00)
    assert evaluate(cfg, _epoch_for(2, 2, 0)).open is False
    # Tuesday 03:00 inside
    assert evaluate(cfg, _epoch_for(2, 3, 0)).open is True
    # Friday afternoon still inside Fri window (before WEEKEND_WINDDOWN_MIN)
    assert evaluate(cfg, _epoch_for(5, 20, 0)).open is True
    # Friday 23:55 is end (exclusive) → seans disi / winddown
    assert evaluate(cfg, _epoch_for(5, 23, 55)).open is False


def test_from_dict_keeps_days_on_sessions():
    cfg = SymbolConfig.from_dict({
        "symbol": "GER40",
        "use_sessions": True,
        "trade_days": [1, 2, 3, 4, 5],
        "sessions": [
            {"start": "03:15", "end": "22:59", "days": [1, 2, 3, 4]},
            {"start": "03:15", "end": "23:55", "days": [5]},
        ],
    })
    assert cfg.sessions[0]["days"] == [1, 2, 3, 4]
    assert cfg.sessions[1]["days"] == [5]
    wins = cfg.session_windows()
    assert wins[0][:2] == (3 * 60 + 15, 22 * 60 + 59)
    assert wins[0][2] == frozenset({1, 2, 3, 4})
