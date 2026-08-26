"""Holdout capture needs per-trade MFE. simulate only stored (ts, ts, r).

26.08 Claude could not compute capture = net_r / sum(mfe_r) on the pin
replay: Result.trade_events has no MFE. The score formula stays untouched;
this is a visible column, not a gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals


def _run(*, peak_high: float, stop_low: float, max_open: int = 1):
    n = 60
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    # Signal 10, fill 11 @ 100. Bar 12 runs to peak_high then bar 13 dies.
    high[12] = peak_high
    close[12] = 100.5
    low[12] = 99.8
    low[13] = stop_low
    close[13] = stop_low + 0.2
    atr = np.full(n, 1.0)
    buy = np.zeros(n, dtype=bool)
    buy[10] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0)
    # simulate reads cache.atr_list, not sig.atr. Pin it so 102-100 is 2.0 R.
    forced = [1.0] * len(cache.atr_list(p.atr_period))
    cache._atr_lists[p.atr_period] = forced
    return backtest.simulate(
        cache, sig, open_, np.zeros(n), point=0.01, p=p,
        entries=np.array([10]), min_stop=0.1, max_open=max_open,
    )


def test_a_two_r_runup_then_stop_records_that_mfe():
    res = _run(peak_high=102.0, stop_low=90.0)
    assert res.trades == 1
    assert res.trade_mfes, "simulate MFE yazmadi - capture hala uretilemez"
    assert res.trade_mfes[0] == pytest.approx(2.0, abs=0.05)
    assert res.capture == pytest.approx(res.net_r / 2.0, abs=0.05)


def test_capture_is_on_as_dict_and_not_in_the_score():
    res = _run(peak_high=102.0, stop_low=90.0)
    payload = res.as_dict(25)
    assert "capture" in payload
    assert payload["capture"] == pytest.approx(res.net_r / sum(res.trade_mfes), abs=0.05)
    # Score is still net_r x sample x dd. A loser scores min(0, net_r).
    assert payload["score"] == res.score(25)
    assert payload["score"] <= 0.0


def test_stacked_path_records_mfe_too():
    res = _run(peak_high=102.0, stop_low=90.0, max_open=2)
    assert res.trades == 1
    assert res.trade_mfes[0] == pytest.approx(2.0, abs=0.05)


def test_a_short_mfe_is_the_coverable_ask_not_the_bid_low():
    """Shorts cover on the ask. MFE used the print low and inflated capture's
    denominator by one spread — the side we already split US30 on.
    """
    n = 60
    high = np.full(n, 100.0)
    low = np.full(n, 100.0)
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    low[12] = 98.0
    high[13] = 110.0
    close[13] = 109.0
    atr = np.full(n, 1.0)
    sell = np.zeros(n, dtype=bool)
    sell[10] = True
    sig = Signals(t3=close, k=close, d=close, atr=atr, adx=np.zeros(n),
                  buy=np.zeros(n, dtype=bool), sell=sell,
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=0.0)
    cache._atr_lists[p.atr_period] = [1.0] * len(cache.atr_list(p.atr_period))
    pad = np.zeros(n)
    pad[12] = 1.0
    res = backtest.simulate(
        cache, sig, open_, np.zeros(n), point=0.01, p=p,
        entries=np.array([10]), min_stop=0.1, trigger_pad=pad,
    )
    assert res.trades == 1
    # Peak favourable is 100 - (98 + 1 pad) = 1, not 100 - 98 = 2.
    assert res.trade_mfes[0] == pytest.approx(1.0, abs=0.05)
