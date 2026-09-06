"""Volume spike gate for burst / channel_break (default off).

``vol_ratio_min`` 0 disables. When set, the signal bar's tick_volume must
be at least that multiple of the trailing SMA(volume, 20).
"""
from __future__ import annotations

import numpy as np

from micofx.strategy import IndicatorCache, Params, _burst, _channel_break


def test_volume_ratio_is_bar_over_sma():
    n = 40
    vol = np.full(n, 10.0)
    vol[30] = 30.0
    # Build cache with this volume from the start (ratio is memoised).
    px = np.full(n, 100.0)
    cache = IndicatorCache(
        px + 1, px - 1, px, times=np.arange(n) * 300, tf_seconds=300,
        open_=px, volume=vol,
    )
    ratio = cache.volume_ratio(20)
    # SMA(20) at i=30 includes the spike → mean = (19*10+30)/20 = 11 → 30/11.
    assert abs(ratio[30] - (30.0 / 11.0)) < 1e-9
    assert ratio[29] == 1.0


def test_burst_vol_ratio_min_blocks_thin_breakout():
    n = 80
    px = np.full(n, 100.0)
    high = px + 2.0
    low = px - 2.0
    high[-5] = 110.0
    low[-5] = 90.0
    close = px.copy()
    close[-5] = 109.5
    open_ = px.copy()
    open_[-5] = 95.0
    thin_vol = np.full(n, 10.0)
    fat_vol = thin_vol.copy()
    fat_vol[-5] = 40.0
    thin_cache = IndicatorCache(
        high, low, close, times=np.arange(n) * 300, tf_seconds=300,
        open_=open_, volume=thin_vol, cost=np.full(n, 0.01),
    )
    fat_cache = IndicatorCache(
        high, low, close, times=np.arange(n) * 300, tf_seconds=300,
        open_=open_, volume=fat_vol, cost=np.full(n, 0.01),
    )
    p_on = Params(strategy="burst", brst_lookback=10, brst_range_z=0.1,
                  brst_close_pct=0.6, cost_rank_max=0.0, adx_min=0.0,
                  vol_ratio_min=1.5, htf_factor=0)
    p_off = Params(strategy="burst", brst_lookback=10, brst_range_z=0.1,
                   brst_close_pct=0.6, cost_rank_max=0.0, adx_min=0.0,
                   vol_ratio_min=0.0, htf_factor=0)
    assert thin_cache.volume_ratio(20)[-5] < 1.5
    assert fat_cache.volume_ratio(20)[-5] >= 1.5
    thin = _burst(thin_cache, p_on)
    assert not thin.buy[-5], "thin volume must not pass vol_ratio_min"
    base = _burst(fat_cache, p_off)
    fat = _burst(fat_cache, p_on)
    if base.buy[-5]:
        assert fat.buy[-5], "fat volume must keep signals the off-gate keeps"


def test_channel_break_respects_vol_ratio_min():
    n = 80
    px = np.linspace(100, 120, n)
    high = px + 0.5
    low = px - 0.5
    close = px.copy()
    open_ = px.copy()
    high[-2] = 200.0
    close[-2] = 199.0
    open_[-2] = 150.0
    thin_vol = np.full(n, 10.0)
    fat_vol = thin_vol.copy()
    fat_vol[-2] = 40.0
    thin_cache = IndicatorCache(
        high, low, close, times=np.arange(n) * 300, tf_seconds=300,
        open_=open_, volume=thin_vol, cost=np.full(n, 0.01),
    )
    fat_cache = IndicatorCache(
        high, low, close, times=np.arange(n) * 300, tf_seconds=300,
        open_=open_, volume=fat_vol, cost=np.full(n, 0.01),
    )
    p_on = Params(strategy="channel_break", chan_lookback=10, chan_buffer_atr=0.0,
                  adx_min=0.0, vol_ratio_min=1.4, htf_factor=0, atr_period=14)
    p_off = Params(strategy="channel_break", chan_lookback=10, chan_buffer_atr=0.0,
                   adx_min=0.0, vol_ratio_min=0.0, htf_factor=0, atr_period=14)
    assert not _channel_break(thin_cache, p_on).buy[-2]
    base = _channel_break(fat_cache, p_off)
    opened = _channel_break(fat_cache, p_on)
    if base.buy[-2]:
        assert opened.buy[-2]
