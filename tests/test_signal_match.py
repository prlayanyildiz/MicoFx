"""signal_match pure-function tests (no panel / MT5)."""
from __future__ import annotations

import numpy as np

from scripts.signal_match import (
    cost_parity,
    filter_autopsy_rows,
    live_style_cost,
    match_autopsy_to_signals,
    replay_style_cost,
    tf_gap_ok,
)


def test_tf_gap_ok_m30():
    assert tf_gap_ok(1800, 0, 1800) is False  # signal 0
    assert tf_gap_ok(2000, 200, 1800) is True   # gap 1800
    assert tf_gap_ok(1100, 200, 1800) is False  # gap 900 = M15 on M30 cfg


def test_filter_autopsy_tf_and_era():
    rows = [
        {"symbol": "NAS100", "signal_bar_time": 1000, "fill_time": 2800, "ticket": 1},
        {"symbol": "NAS100", "signal_bar_time": 1000, "fill_time": 1900, "ticket": 2},  # M15 gap
        {"symbol": "NAS100", "signal_bar_time": 5000, "fill_time": 6800, "ticket": 3},
        {"symbol": "GER40", "signal_bar_time": 1000, "fill_time": 2800, "ticket": 4},
    ]
    got = filter_autopsy_rows(rows, symbol="NAS100", tf_sec=1800, since_ts=3000)
    assert [r["ticket"] for r in got] == [3]


def test_cost_parity_identical_ok():
    x = np.array([1.0, 1.1, 0.9, 1.0])
    rep = cost_parity(x, x)
    assert rep["diverge"] is False


def test_cost_parity_scaled_diverges():
    live = np.ones(100)
    replay = live * 2.0
    rep = cost_parity(live, replay)
    assert rep["diverge"] is True


def test_live_vs_replay_cost_helpers_differ_when_scale_not_one():
    spread = np.array([10.0, 0.0, 10.0, 12.0])  # 0 gets imputed in replay
    live = live_style_cost(spread, point=0.01, commission=0.0)
    rep = replay_style_cost(spread, point=0.01, scale=1.2, commission=0.0)
    assert live.shape == rep.shape
    assert float(np.median(np.abs(live - rep))) > 0


def test_match_autopsy_miss_rate():
    autopsy = [
        {"signal_bar_time": 100, "side": "buy", "ticket": 1, "r_realised": -1},
        {"signal_bar_time": 200, "side": "sell", "ticket": 2, "r_realised": 1},
        {"signal_bar_time": 300, "side": "buy", "ticket": 3, "r_realised": -1},
    ]
    all_sig = {100, 200}
    buy, sell = {100}, {200}
    m = match_autopsy_to_signals(
        autopsy, all_sig, buy, sell, time_lo=0, time_hi=1000)
    assert m["covered_in_snapshot"] == 3
    assert m["hit"] == 2
    assert m["miss"] == 1
    assert m["miss_rate"] == round(1 / 3, 4)
