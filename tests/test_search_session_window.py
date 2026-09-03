"""Search pre-step: pick a session window from charged holdout, not a grid axis.

Claude 03.09 19:05: NAS100 24h +57R PF1.05 vs 14-22 +180R PF1.30. Sessions
are not OPT_FIELDS; this only chooses the window the sweep (and a later
apply persist) will use.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import (
    SEARCH_SESSION_WINDOWS,
    Optimizer,
    _choose_search_sessions,
    _is_all_hours_sessions,
    _session_holdout_ok,
)


def _hold(net_r: float, pf: float, trades: int = 80) -> dict:
    return {"net_r": net_r, "profit_factor": pf, "trades": trades, "max_dd_r": 40.0}


def test_full_day_fails_ok_14_22_wins():
    """NAS100-shaped: 24h fails the slice, 14-22 is the search window."""
    full = [{"start": "00:00", "end": "23:59"}]
    win = [{"start": "14:00", "end": "22:00"}]
    picked = _choose_search_sessions(full, [
        (full, _hold(57.0, 1.05)),
        (win, _hold(180.6, 1.30)),
        ([{"start": "08:00", "end": "16:00"}], _hold(20.0, 1.12)),
    ])
    assert picked == win


def test_keep_current_when_already_best():
    """JPN225-shaped: live 23-08 already wins — do not rewrite sessions."""
    night = [{"start": "23:00", "end": "08:00"}]
    picked = _choose_search_sessions(night, [
        (night, _hold(60.41, 1.35)),
        ([{"start": "14:00", "end": "22:00"}], _hold(10.0, 1.20)),
    ])
    assert picked is None


def test_weak_windows_do_not_replace_live():
    assert _session_holdout_ok(_hold(57.0, 1.05)) is False
    assert _session_holdout_ok(_hold(180.6, 1.30)) is True
    picked = _choose_search_sessions(
        [{"start": "00:00", "end": "09:00"}],
        [
            ([{"start": "00:00", "end": "09:00"}], _hold(-5.0, 0.9)),
            ([{"start": "14:00", "end": "22:00"}], _hold(12.0, 1.08, trades=40)),
        ],
    )
    assert picked is None


def test_search_windows_cover_claude_set():
    keys = {(w[0]["start"], w[0]["end"]) for w in SEARCH_SESSION_WINDOWS}
    assert ("00:00", "23:59") in keys
    assert ("14:00", "22:00") in keys
    assert ("23:00", "08:00") in keys
    assert ("08:00", "16:00") in keys


def test_pick_search_sessions_uses_costed_overlay():
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.system = SystemConfig(charge_costs=True)
    cfg = SymbolConfig(
        symbol="NAS100", magic=1, strategy="mtf_pullback", timeframe="M30",
        sessions=[{"start": "00:00", "end": "23:59"}], use_sessions=True)
    opt.store.symbols = {"NAS100": cfg}

    def fake_costed(symbol, timeframe, strategy, params, **kwargs):
        sessions = kwargs.get("sessions")
        if sessions is None:
            sessions = cfg.sessions
        start = sessions[0]["start"]
        if start == "14:00":
            return _hold(180.6, 1.30)
        if start == "00:00":
            return _hold(57.0, 1.05)
        return _hold(20.0, 1.12)

    opt._holdout_costed = fake_costed  # type: ignore[method-assign]
    assert opt._pick_search_sessions(cfg) == [{"start": "14:00", "end": "22:00"}]


def test_pick_ignores_leftover_windows_when_sessions_off():
    """JPN225 19:53: use_sessions=false but sessions list still 23-08.

    Pre-step must treat live as 00-24, not sticky-compare against the
    unread leftover night window (Claude 19:51: 24h +143R vs 23-08 +46R).
    """
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.system = SystemConfig(charge_costs=True)
    cfg = SymbolConfig(
        symbol="JPN225", magic=1, strategy="burst", timeframe="M30",
        sessions=[{"start": "23:00", "end": "08:00"}], use_sessions=False)
    opt.store.symbols = {"JPN225": cfg}

    def fake_costed(symbol, timeframe, strategy, params, **kwargs):
        sessions = kwargs.get("sessions")
        start = (sessions or [{}])[0].get("start")
        if start == "00:00":
            return {**_hold(143.7, 1.56), "score": 122.7}
        if start == "23:00":
            return {**_hold(46.2, 1.44), "score": 31.9}
        return {**_hold(20.0, 1.12), "score": 10.0}

    opt._holdout_costed = fake_costed  # type: ignore[method-assign]
    assert opt._pick_search_sessions(cfg) is None


def test_near_tie_switches_when_challenger_dd_is_tighter():
    """NAS100 14-22 vs 15-21: score +4.5% sticky, but dd 91->57 must switch.

    Claude 20:06: 15-21 is the apply-shaped window; plain +15% score sticky
    would keep the fragile 14-22 cell and risk another F6 refuse.
    """
    live = [{"start": "14:00", "end": "22:00"}]
    tight = [{"start": "15:00", "end": "21:00"}]
    picked = _choose_search_sessions(live, [
        (live, {**_hold(121.4, 1.18), "score": 69.4, "max_dd_r": 91.0}),
        (tight, {**_hold(110.4, 1.20), "score": 72.5, "max_dd_r": 57.7}),
    ])
    assert picked == tight


def test_near_tie_stays_when_dd_is_not_tighter():
    live = [{"start": "14:00", "end": "22:00"}]
    peer = [{"start": "15:00", "end": "21:00"}]
    picked = _choose_search_sessions(live, [
        (live, {**_hold(100.0, 1.20), "score": 69.4, "max_dd_r": 50.0}),
        (peer, {**_hold(105.0, 1.20), "score": 72.5, "max_dd_r": 48.0}),
    ])
    assert picked is None


def test_sticky_protects_live_when_pf_just_below_ok_gate():
    """NAS100 20:44: live 15-21 PF~1.09 failed ok; 08-16 became best_ok and
    the search then produced zero validated candidates under that clock.

    Pre-step scores the *current* params under each mask. Live params were
    not tuned for 08-16, so a soft PF miss on the operator window must not
    waive sticky and hand the sweep a different clock.
    """
    live = [{"start": "15:00", "end": "21:00"}]
    other = [{"start": "08:00", "end": "16:00"}]
    picked = _choose_search_sessions(live, [
        (live, {**_hold(110.4, 1.09), "score": 70.0, "max_dd_r": 57.7}),
        (other, {**_hold(95.0, 1.22), "score": 78.0, "max_dd_r": 40.0}),
    ])
    assert picked is None


def test_soft_sticky_still_yields_to_clear_score_jump():
    live = [{"start": "15:00", "end": "21:00"}]
    other = [{"start": "08:00", "end": "16:00"}]
    picked = _choose_search_sessions(live, [
        (live, {**_hold(110.4, 1.09), "score": 70.0, "max_dd_r": 57.7}),
        (other, {**_hold(160.0, 1.30), "score": 95.0, "max_dd_r": 40.0}),
    ])
    assert picked == other


def test_healthy_live_keeps_through_mild_prestep_bump():
    """NAS100 21:19 measured: 15-21 sc63.7/PF1.18 vs 08-16 sc73.8 (+16%).

    +15% sticky let 08-16 win; WFO under that clock then produced zero
    validated candidates. Healthy live (full ok) needs +25%.
    """
    live = [{"start": "15:00", "end": "21:00"}]
    other = [{"start": "08:00", "end": "16:00"}]
    picked = _choose_search_sessions(live, [
        (live, {**_hold(110.4, 1.18), "score": 63.7, "max_dd_r": 57.7}),
        (other, {**_hold(120.0, 1.20), "score": 73.8, "max_dd_r": 46.6}),
    ])
    assert picked is None


def test_persist_all_hours_clears_use_sessions():
    assert _is_all_hours_sessions([{"start": "00:00", "end": "23:59"}]) is True
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt._persist_search_sessions("XAUUSD", [{"start": "00:00", "end": "23:59"}])
    patch = opt.store.update_symbol.call_args[0][1]
    assert patch["use_sessions"] is False
    opt._persist_search_sessions("NAS100", [{"start": "14:00", "end": "22:00"}])
    patch = opt.store.update_symbol.call_args[0][1]
    assert patch["use_sessions"] is True


def test_0000_2359_drops_last_minute_unlike_sessions_off():
    monday_2359 = np.array([4 * 86400 + 23 * 3600 + 59 * 60], dtype=np.float64)
    on = SymbolConfig(
        symbol="X", magic=1, use_sessions=True, trade_days=[1, 2, 3, 4, 5],
        sessions=[{"start": "00:00", "end": "23:59"}])
    off = SymbolConfig(
        symbol="X", magic=1, use_sessions=False, trade_days=[1, 2, 3, 4, 5])
    assert bool(backtest.session_mask(off, monday_2359)[0]) is True
    assert bool(backtest.session_mask(on, monday_2359)[0]) is False
