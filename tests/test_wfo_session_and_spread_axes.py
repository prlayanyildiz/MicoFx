"""WFO axes: session shortlist fan-out + per-symbol spread-cap from bars.

Claude 03.09 23:10/23:13 night: pre-step alone picked one clock before the
sweep; WFO+F6 should choose among a short filtered list. max_spread_atr
stored grid is static — search must price this symbol's own spread/ATR
percentiles (p40/p55/p70) so US30/JPN225 stop admitting over-cap losers.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import (
    Optimizer,
    _sessions_key,
    spread_cap_search_axis,
)


def _hold(net_r: float, pf: float, trades: int = 80, dd: float = 40.0) -> dict:
    return {
        "net_r": net_r, "profit_factor": pf, "trades": trades,
        "max_dd_r": dd, "score": net_r * 0.5,
    }


def _bars(n: int = 800, *, ratios: list[float] | None = None):
    """Synthetic bars: constant ATR=1 price unit, spread = ratio * ATR / point."""
    point = 0.01
    atr_price = 1.0
    if ratios is None:
        # Mostly cheap, some mid, some wide.
        ratios = ([0.03] * 300 + [0.06] * 250 + [0.10] * 250)
    ratios = (ratios * ((n // len(ratios)) + 1))[:n]
    spread_pts = np.array([r * atr_price / point for r in ratios], dtype=float)
    close = np.linspace(100.0, 100.0 + n * 0.01, n)
    high = close + atr_price
    low = close - atr_price
    open_ = close.copy()
    return SimpleNamespace(
        open=open_, high=high, low=low, close=close,
        spread=spread_pts, time=np.arange(n, dtype=np.int64) * 1800,
    ), point


def test_spread_cap_axis_uses_symbol_percentiles():
    bars, point = _bars()
    axis = spread_cap_search_axis(bars, point, live_cap=0.08)
    assert 3 <= len(axis) <= 5
    assert all(isinstance(v, float) for v in axis)
    assert axis == sorted(axis)
    # Floor / live / distribution should all be representable.
    assert min(axis) >= 0.03
    assert max(axis) <= 0.50


def test_spread_cap_axis_includes_live_cap_when_in_band():
    bars, point = _bars()
    axis = spread_cap_search_axis(bars, point, live_cap=0.08)
    assert 0.08 in axis


def test_session_shortlist_keeps_live_and_up_to_two_ok_challengers():
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.system = SystemConfig(charge_costs=True)
    cfg = SymbolConfig(
        symbol="NAS100", magic=1, strategy="mtf_pullback", timeframe="M30",
        sessions=[{"start": "15:00", "end": "21:00"}], use_sessions=True)
    opt.store.symbols = {"NAS100": cfg}

    def fake_costed(symbol, timeframe, strategy, params, **kwargs):
        sessions = kwargs.get("sessions") or cfg.sessions
        start = sessions[0]["start"]
        table = {
            "15:00": _hold(101.0, 1.19, dd=57.0),
            "14:00": _hold(180.0, 1.30, dd=40.0),
            "08:00": _hold(90.0, 1.20, dd=50.0),
            "00:00": _hold(57.0, 1.05, dd=110.0),  # fails ok
            "23:00": _hold(10.0, 1.12, dd=20.0),
        }
        return table.get(start, _hold(20.0, 1.12))

    opt._holdout_costed = fake_costed  # type: ignore[method-assign]
    opt._bars_for_holdout = lambda *a, **k: object()  # unused when costed faked
    short = opt._session_search_shortlist(cfg)
    keys = [_sessions_key(w) for w in short]
    assert _sessions_key([{"start": "15:00", "end": "21:00"}]) in keys  # live always
    assert len(short) <= 3
    assert _sessions_key([{"start": "14:00", "end": "22:00"}]) in keys  # strongest ok
    assert _sessions_key([{"start": "00:00", "end": "23:59"}]) not in keys  # PF miss


def test_plan_fans_out_one_job_per_session_shortlist_member():
    """Each shortlisted clock becomes its own (tf, family) sweep job."""
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.system = SystemConfig(charge_costs=True, opt_max_workers=1)
    opt.store.defaults = {"optimizer": {}}
    opt.client = MagicMock()
    cfg = SymbolConfig(
        symbol="US30", magic=1, strategy="channel_break", timeframe="M30",
        sessions=[{"start": "08:00", "end": "16:00"}], use_sessions=True,
        max_spread_atr=0.08)
    opt.store.symbols = {"US30": cfg}
    opt.store.opt_params = MagicMock(return_value={
        "strategies": ["channel_break"],
        "timeframes": ["M30"],
        "max_combos": 50,
        "grid": {"sl_atr_mult": [1.5], "trail_start_atr": [0.5],
                 "trail_step_atr": [2.0], "max_spread_atr": [0.05, 0.08]},
        "strategy_grids": {},
    })

    live = [{"start": "08:00", "end": "16:00"}]
    other = [{"start": "14:00", "end": "22:00"}]
    opt._session_search_shortlist = lambda c: [live, other]  # type: ignore
    opt._spread_scale = lambda s: 1.0
    opt._ensure_sweep_bars_dir = lambda: Path(".")

    class _Bars:
        def __init__(self, n: int = 700) -> None:
            self.open = np.ones(n)
            self.high = np.ones(n) + 1
            self.low = np.ones(n) - 1
            self.close = np.ones(n)
            self.spread = np.ones(n)
            self.time = np.arange(n) * 1800
            self.forming_time = 0

        def __len__(self) -> int:
            return self.close.size

    bars = _Bars()
    opt.client.bars = MagicMock(return_value=bars)
    opt.client.info = MagicMock(return_value={
        "point": 0.01, "tick_value": 1.0, "tick_size": 0.01})
    opt.client.min_stop_distance = MagicMock(return_value=0.0)
    opt._bar_snap = {}
    opt._exit_grid_for = lambda *a, **k: {
        "sl_atr_mult": [1.5], "trail_start_atr": [0.5],
        "trail_step_atr": [2.0], "max_spread_atr": [0.05, 0.08],
    }

    # Avoid writing real npy in test — stub write_sweep_bars via import path
    import micofx.optimizer as optmod
    orig = optmod.write_sweep_bars
    optmod.write_sweep_bars = lambda path, bars: path  # type: ignore
    try:
        plan = opt._plan_symbol(
            cfg, lookback_days=0, bar_cap=700,
            variants=[{"strategy": "channel_break", "grid": {}, "own": set(),
                       "shared": {}}],
            min_trades=40, segments=5, max_combos=50, min_positive=0.6,
            plateau=0.5, timeframes=["M30"], refine_rounds=0, tf_allow=None,
            alloc=None,
        )
    finally:
        optmod.write_sweep_bars = orig

    jobs = plan["jobs"]
    assert len(jobs) == 2
    sess_keys = {_sessions_key(j.get("search_sessions")) for j in jobs}
    assert sess_keys == {_sessions_key(live), _sessions_key(other)}
    for j in jobs:
        assert "search_sessions" in j
        assert j["cfg"]["sessions"] == j["search_sessions"]
