from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from . import indicators as ind
from .models import SymbolConfig

STOCH_MID = 50.0


@dataclass
class Params:
    """Flat parameter view so the optimizer can vary values without a full config."""

    strategy: str = "t3_stoch"
    session_start_min: int = 0       # anchors ORB and VWAP to the trading session

    # ---- Bollinger/Keltner squeeze breakout ----
    sqz_length: int = 20
    sqz_bb_sd: float = 2.0
    sqz_kc_atr: float = 1.5
    sqz_momentum_len: int = 12

    # ---- order-flow-proxy exhaustion reversion ----
    flow_length: int = 20
    flow_z: float = 2.0
    flow_divergence: bool = True

    # ---- higher-timeframe trend pullback ----
    pull_fast: int = 8
    pull_depth_atr: float = 0.5
    pull_max_bars: int = 6

    # ---- cost-scaled micro mean reversion (M5-native scalp) ----
    mr_fast: int = 6
    mr_stretch_cost: float = 4.0
    mr_confirm: bool = True

    # ---- range-expansion momentum burst (M5-native scalp) ----
    brst_lookback: int = 20
    brst_range_z: float = 1.5
    brst_close_pct: float = 0.7

    # ---- Tillson T3 ribbon (fast/slow T3 cross) ----
    t3_fast: int = 5                 # fast T3 length
    t3_slow_mult: float = 3.0        # slow T3 length = fast * this
    t3_slope_atr: float = 0.0        # 0 disables; min |slow T3 slope| per bar, in ATR
    t3_fast_vf: float = 0.0          # fast line's own volume factor; 0 inherits t3_volume_factor

    # ---- T3 slope-quality (curvature) filter, shared by the T3 families ----
    t3_accel_min: float = 0.0        # 0 disables; min T3 second difference, in ATR

    # ---- optional SuperTrend confirmation (dual_t3 only) ----
    st_period: int = 10              # ATR period of the SuperTrend envelope
    st_mult: float = 0.0             # 0 disables the confirmation entirely

    # ---- adaptive cost-regime gate, shared by the scalping families ----
    cost_rank_max: float = 0.0       # 0 disables; percentile ceiling on cost/range

    # ---- opening range breakout ----
    orb_minutes: int = 30
    orb_buffer_atr: float = 0.1
    orb_retest: bool = False         # wait for a pullback + reclaim instead of chasing the break

    # ---- Donchian breakout ----
    don_length: int = 20
    don_buffer_atr: float = 0.0
    don_squeeze: float = 0.0         # 0 disables; channel-width percentile ceiling

    # ---- VWAP mean reversion ----
    vwap_sd: float = 2.0
    vwap_reentry: bool = True        # wait for price to turn back toward VWAP
    adx_max: float = 0.0             # 0 disables; reversion dies in strong trends

    # ---- liquidity sweep / stop hunt reversal ----
    swp_lookback: int = 20           # bars defining the swing high/low that gets swept
    swp_wick_atr: float = 0.15       # how far past that swing the wick must reach, in ATR

    # ---- MACD histogram zero-cross ----
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # ---- WaveTrend crossover ----
    wt_channel_len: int = 10
    wt_avg_len: int = 21

    # ---- Slow Stochastic crossover (price range, not RSI) ----
    stoch_k_period: int = 10
    stoch_k_smooth: int = 6
    stoch_d_smooth: int = 3

    # ---- Parabolic SAR flip ----
    psar_af_step: float = 0.02
    psar_af_max: float = 0.2

    # ---- TRIX zero-cross (slow, triple-smoothed) ----
    trix_length: int = 14

    # ---- Aroon oscillator zero-cross ----
    aroon_length: int = 14

    t3_length: int = 6
    t3_volume_factor: float = 0.7
    rsi_length: int = 9
    stoch_length: int = 9
    smooth_k: int = 3
    smooth_d: int = 3
    stoch_band: float = 20.0
    stoch_extreme: float = 80.0
    htf_factor: int = 6
    htf_mode: str = "t3"
    atr_period: int = 14
    adx_period: int = 14
    adx_min: float = 0.0
    # Exit model: hard ATR stop + ATR trail, nothing else. See SymbolConfig.
    sl_atr_mult: float = 1.2
    trail_start_atr: float = 0.8
    trail_step_atr: float = 0.6
    trail_mode: str = "atr"          # "atr" | "structure" | "hybrid"
    trail_lookback: int = 5          # bars to look back for swing high/low (structure/hybrid)
    cooldown_sec: int = 0            # live engine caps to 2 bars of TF; BT mirrors that
    max_spread_atr: float = 0.0
    min_atr_ratio: float = 0.0
    min_body_ratio: float = 0.0
    atr_pct_min: float = 0.0

    @classmethod
    def from_config(cls, cfg: SymbolConfig, **overrides: Any) -> "Params":
        base = {f: getattr(cfg, f) for f in cls.__dataclass_fields__ if hasattr(cfg, f)}
        base["session_start_min"] = cfg.session_start_minutes()
        base.update({k: v for k, v in overrides.items() if k in cls.__dataclass_fields__})
        return cls(**base)

    def key(self) -> tuple:
        """Identity of the *signal* series this parameter set produces.

        Every field a strategy family reads when it builds buy/sell must appear
        here: the optimizer caches signals against this key while it sweeps the
        exit grid, so a missing field would silently reuse the wrong series.
        Exit-side fields (stops, targets, trailing, partials, spread gate) are
        deliberately absent - they never move a signal bar.
        """
        return (self.strategy, self.t3_length, self.t3_volume_factor, self.rsi_length,
                self.stoch_length, self.smooth_k, self.smooth_d, self.stoch_band,
                self.stoch_extreme, self.atr_period, self.adx_period, self.adx_min,
                self.adx_max, self.htf_factor, self.htf_mode, self.min_body_ratio,
                self.atr_pct_min, self.orb_minutes, self.orb_buffer_atr, self.orb_retest,
                self.don_length, self.don_buffer_atr, self.don_squeeze,
                self.vwap_sd, self.vwap_reentry, self.session_start_min,
                self.sqz_length, self.sqz_bb_sd, self.sqz_kc_atr, self.sqz_momentum_len,
                self.flow_length, self.flow_z, self.flow_divergence,
                self.pull_fast, self.pull_depth_atr, self.pull_max_bars,
                self.mr_fast, self.mr_stretch_cost, self.mr_confirm,
                self.brst_lookback, self.brst_range_z, self.brst_close_pct,
                self.t3_fast, self.t3_slow_mult, self.t3_slope_atr, self.t3_fast_vf,
                self.t3_accel_min,
                self.st_period, self.st_mult,
                self.swp_lookback, self.swp_wick_atr,
                self.cost_rank_max,
                self.macd_fast, self.macd_slow, self.macd_signal,
                self.wt_channel_len, self.wt_avg_len,
                self.stoch_k_period, self.stoch_k_smooth, self.stoch_d_smooth,
                self.psar_af_step, self.psar_af_max, self.trix_length,
                self.aroon_length)


class IndicatorCache:
    """Memoises indicator series so a parameter sweep recomputes only what changed."""

    def __init__(self, high: np.ndarray, low: np.ndarray, close: np.ndarray,
                 times: np.ndarray | None = None, tf_seconds: int = 300,
                 open_: np.ndarray | None = None, volume: np.ndarray | None = None,
                 cost: np.ndarray | None = None) -> None:
        self.high, self.low, self.close = high, low, close
        # Round-turn transaction cost per bar in *price* units (bar spread plus
        # commission). The scalping families size their entry threshold against
        # this rather than against ATR, so it has to be the real number the
        # backtest charges - not a proxy. ``None`` means the caller could not
        # supply it, and those families then produce no signals at all rather
        # than silently trading a made-up cost.
        self._cost = np.asarray(cost, dtype=np.float64) if cost is not None else None
        self._cost_rank: dict[int, np.ndarray] = {}
        self.open = open_ if open_ is not None else close
        self.times = times if times is not None else np.arange(close.size, dtype=np.int64) * tf_seconds
        self.tf_seconds = int(tf_seconds)
        self._t3: dict[tuple, np.ndarray] = {}
        self._stoch: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
        self._atr: dict[int, np.ndarray] = {}
        self._adx: dict[int, np.ndarray] = {}
        self._htf: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
        self._rank: dict[tuple, np.ndarray] = {}
        self._vwap: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        self._orb: dict[tuple, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self._don: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self._squeeze: dict[tuple, np.ndarray] = {}
        self._session: dict[int, np.ndarray] = {}
        self._body: np.ndarray | None = None
        self._bb: dict[tuple, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self._kc: dict[tuple, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self._slope: dict[int, np.ndarray] = {}
        self._ema: dict[int, np.ndarray] = {}
        self._flow: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
        self._supertrend: dict[tuple, np.ndarray] = {}
        self._macd: dict[tuple, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
        self._wavetrend: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
        self._stoch_slow: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
        self._psar: dict[tuple, np.ndarray] = {}
        self._trix: dict[int, np.ndarray] = {}
        self._aroon: dict[int, np.ndarray] = {}
        self._delta: np.ndarray | None = None
        self._lists: tuple | None = None
        self._atr_lists: dict[int, list] = {}
        self.volume = volume if volume is not None else np.ones(close.size)
        self._src = ind.t3_source(high, low, close)

    # ---- transaction cost -------------------------------------------------

    def cost(self) -> np.ndarray | None:
        """Round-turn cost per bar in price units, or None when unavailable."""
        return self._cost

    def cost_ok(self, rank_max: float, window: int = 240) -> np.ndarray:
        """Bars whose cost is cheap *relative to what this market usually is*.

        A static spread ceiling cannot know that GER40's spread at the cash open
        is normal and the same number at 23:00 is extortionate. This ranks the
        bar's cost against the range it is trying to capture, then ranks *that*
        ratio inside its own trailing distribution, so the gate follows the
        symbol and the session instead of a hard-coded constant. On raw FX the
        bar spread field is flat and the whole cost is a fixed commission, so
        the ratio still moves - with the range rather than the spread - and the
        gate reduces to "only trade bars big enough to pay for themselves".
        """
        size = self.close.size
        if rank_max <= 0 or rank_max >= 1:
            return np.ones(size, dtype=bool)          # gate intentionally off
        if self._cost is None:
            # Gate is requested (rank_max > 0) but there is nothing to rank -
            # "unknown cost" is not "cheap enough", it is the one case this
            # filter exists to catch. micro_rev already refuses to trade blind
            # when cost is unavailable; every other cost_ok() caller (burst,
            # t3_ribbon) was silently getting an all-pass instead, which turned
            # a real cost gate into a no-op exactly when it mattered.
            return np.zeros(size, dtype=bool)
        key = int(window)
        rank = self._cost_rank.get(key)
        if rank is None:
            span = self.high - self.low
            ratio = self._cost / np.where(span > 1e-12, span, 1e-12)
            rank = ind.rolling_rank(ratio, key)
            self._cost_rank[key] = rank
        return rank <= float(rank_max)

    # ---- Bollinger / Keltner squeeze --------------------------------------

    def bollinger(self, length: int, sd: float):
        key = (int(length), round(float(sd), 4))
        if key not in self._bb:
            self._bb[key] = ind.bollinger(self.close, key[0], key[1])
        return self._bb[key]

    def keltner(self, length: int, atr_mult: float):
        key = (int(length), round(float(atr_mult), 4))
        if key not in self._kc:
            self._kc[key] = ind.keltner(self.high, self.low, self.close, key[0], key[1])
        return self._kc[key]

    def slope(self, length: int) -> np.ndarray:
        key = int(length)
        if key not in self._slope:
            self._slope[key] = ind.linreg_slope(self.close, key)
        return self._slope[key]

    def ema(self, length: int) -> np.ndarray:
        key = int(length)
        if key not in self._ema:
            self._ema[key] = ind.ema(self.close, key)
        return self._ema[key]

    # ---- order-flow proxy -------------------------------------------------

    def delta(self) -> np.ndarray:
        if self._delta is None:
            self._delta = ind.delta_proxy(self.open, self.high, self.low,
                                          self.close, self.volume)
        return self._delta

    def flow(self, length: int) -> tuple[np.ndarray, np.ndarray]:
        """Trailing signed-volume sum and its z-score against its own history."""
        key = (int(length), 200)
        if key not in self._flow:
            run = ind.rolling_sum(self.delta(), key[0])
            self._flow[key] = (run, ind.zscore(run, key[1]))
        return self._flow[key]

    def vwap(self, session_start_min: int) -> tuple[np.ndarray, np.ndarray]:
        key = int(session_start_min)
        if key not in self._vwap:
            self._vwap[key] = ind.session_vwap(self.times, self.high, self.low, self.close,
                                               self.volume, key)
        return self._vwap[key]

    def opening_range(self, session_start_min: int, minutes: int):
        key = (int(session_start_min), int(minutes))
        if key not in self._orb:
            self._orb[key] = ind.opening_range(self.times, self.high, self.low, key[0], key[1])
        return self._orb[key]

    def donchian(self, length: int):
        key = int(length)
        if key not in self._don:
            self._don[key] = ind.donchian(self.high, self.low, key)
        return self._don[key]

    def squeeze_rank(self, length: int, window: int = 200) -> np.ndarray:
        """Where the current channel width sits in its own recent range, 0..1."""
        key = (int(length), int(window))
        if key not in self._squeeze:
            hi, lo, _ = self.donchian(key[0])
            self._squeeze[key] = ind.rolling_rank(hi - lo, key[1])
        return self._squeeze[key]

    def session_id(self, session_start_min: int) -> np.ndarray:
        key = int(session_start_min)
        if key not in self._session:
            self._session[key] = ind.session_index(self.times, key)
        return self._session[key]

    def t3(self, length: int, vf: float) -> np.ndarray:
        key = (int(length), round(float(vf), 4))
        if key not in self._t3:
            self._t3[key] = ind.tillson_t3(self._src, key[0], key[1])
        return self._t3[key]

    def htf(self, factor: int, length: int, vf: float) -> tuple[np.ndarray, np.ndarray]:
        key = (int(factor), int(length), round(float(vf), 4))
        if key not in self._htf:
            self._htf[key] = ind.htf_t3_trend(
                self.times, self.high, self.low, self.close,
                self.tf_seconds * key[0], key[1], key[2],
            )
        return self._htf[key]

    def stoch(self, rsi_len: int, stoch_len: int, k: int, d: int) -> tuple[np.ndarray, np.ndarray]:
        key = (int(rsi_len), int(stoch_len), int(k), int(d))
        if key not in self._stoch:
            self._stoch[key] = ind.stoch_rsi(self.close, *key)
        return self._stoch[key]

    def supertrend(self, period: int, multiplier: float) -> np.ndarray:
        """SuperTrend direction (+1/-1); an ATR trailing band read as a trend."""
        key = (int(period), round(float(multiplier), 4))
        if key not in self._supertrend:
            self._supertrend[key] = ind.supertrend(self.high, self.low, self.close,
                                                   key[0], key[1])
        return self._supertrend[key]

    def atr(self, period: int) -> np.ndarray:
        key = int(period)
        if key not in self._atr:
            self._atr[key] = ind.atr(self.high, self.low, self.close, key)
        return self._atr[key]

    def macd(self, fast: int, slow: int, signal: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        key = (int(fast), int(slow), int(signal))
        if key not in self._macd:
            self._macd[key] = ind.macd(self.close, *key)
        return self._macd[key]

    def wavetrend(self, channel_len: int, avg_len: int) -> tuple[np.ndarray, np.ndarray]:
        key = (int(channel_len), int(avg_len))
        if key not in self._wavetrend:
            self._wavetrend[key] = ind.wavetrend(self.high, self.low, self.close, *key)
        return self._wavetrend[key]

    def stoch_slow(self, k_period: int, k_smooth: int, d_smooth: int) -> tuple[np.ndarray, np.ndarray]:
        key = (int(k_period), int(k_smooth), int(d_smooth))
        if key not in self._stoch_slow:
            self._stoch_slow[key] = ind.stochastic_slow(self.high, self.low, self.close, *key)
        return self._stoch_slow[key]

    def psar(self, af_step: float, af_max: float) -> np.ndarray:
        key = (round(float(af_step), 5), round(float(af_max), 5))
        if key not in self._psar:
            self._psar[key] = ind.parabolic_sar(self.high, self.low, *key)
        return self._psar[key]

    def trix(self, length: int) -> np.ndarray:
        key = int(length)
        if key not in self._trix:
            self._trix[key] = ind.trix(self.close, key)
        return self._trix[key]

    def aroon(self, length: int) -> np.ndarray:
        key = int(length)
        if key not in self._aroon:
            self._aroon[key] = ind.aroon(self.high, self.low, key)
        return self._aroon[key]

    # ---- python-list views ------------------------------------------------
    # The backtest's trade-management loop is inherently sequential and reads a
    # handful of scalars per bar. Indexing a Python list is several times
    # cheaper than unboxing a numpy scalar, and these series are identical for
    # every combination in a sweep, so they are built once per cache.

    def lists(self) -> tuple[list, list, list, list]:
        if self._lists is None:
            self._lists = (self.high.tolist(), self.low.tolist(),
                           self.close.tolist(), self.open.tolist())
        return self._lists

    def atr_list(self, period: int) -> list:
        key = int(period)
        if key not in self._atr_lists:
            self._atr_lists[key] = self.atr(key).tolist()
        return self._atr_lists[key]

    def atr_rank(self, period: int, window: int = 200) -> np.ndarray:
        key = (int(period), int(window))
        if key not in self._rank:
            self._rank[key] = ind.rolling_rank(self.atr(key[0]), key[1])
        return self._rank[key]

    def body_ratio(self) -> np.ndarray:
        if self._body is None:
            span = self.high - self.low
            body = np.abs(self.close - self.open)
            self._body = np.where(span > 1e-12, body / np.where(span > 1e-12, span, 1.0), 0.0)
        return self._body

    def adx(self, period: int) -> np.ndarray:
        key = int(period)
        if key not in self._adx:
            self._adx[key] = ind.adx(self.high, self.low, self.close, key)
        return self._adx[key]


@dataclass
class Signals:
    t3: np.ndarray
    k: np.ndarray
    d: np.ndarray
    atr: np.ndarray
    adx: np.ndarray
    buy: np.ndarray
    sell: np.ndarray
    htf_up: np.ndarray
    htf_down: np.ndarray

    def last(self) -> dict[str, Any]:
        if self.t3.size < 2:
            return {}
        i = -1
        buy = bool(self.buy[i]) and not bool(self.sell[i])
        sell = bool(self.sell[i]) and not bool(self.buy[i])
        return {
            "t3": float(self.t3[i]),
            "t3_rising": bool(self.t3[i] > self.t3[i - 1]),
            "k": float(self.k[i]), "d": float(self.d[i]),
            "atr": float(self.atr[i]), "adx": float(self.adx[i]),
            "buy": buy,
            "sell": sell,
            "htf": 1 if self.htf_up[i] else (-1 if self.htf_down[i] else 0),
        }


def compute(cache: IndicatorCache, p: Params) -> Signals:
    """Route to the configured strategy family."""
    builder = _FAMILIES.get(p.strategy, _t3_stoch)
    return builder(cache, p)


def _common(cache: IndicatorCache, p: Params):
    """Shared series every family reports back to the UI and the risk model."""
    t3 = cache.t3(p.t3_length, p.t3_volume_factor)
    k, d = cache.stoch(p.rsi_length, p.stoch_length, p.smooth_k, p.smooth_d)
    atr_series = cache.atr(p.atr_period)
    need_adx = p.adx_min > 0 or p.adx_max > 0
    adx_series = cache.adx(p.adx_period) if need_adx else np.zeros(cache.close.size)
    return t3, k, d, atr_series, adx_series


def _regime(p: Params, adx_series: np.ndarray, size: int) -> np.ndarray:
    ok = np.ones(size, dtype=bool)
    if p.adx_min > 0:
        ok &= adx_series >= p.adx_min
    if p.adx_max > 0:
        ok &= adx_series <= p.adx_max
    return ok


def _trend_gate(cache: IndicatorCache, p: Params) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    size = cache.close.size
    if p.htf_mode == "t3" and p.htf_factor > 1:
        up, down = cache.htf(p.htf_factor, p.t3_length, p.t3_volume_factor)
        return up, down, up, down
    zero = np.zeros(size, dtype=bool)
    allow = np.ones(size, dtype=bool)
    return zero, zero, allow, allow


def _t3_accel(line: np.ndarray, atr_series: np.ndarray) -> np.ndarray:
    """Curvature of a T3 line: its second difference, normalised by ATR.

    The first difference only says the line is going up; it says nothing about
    whether the move is still building or already rolling over. Tillson's own
    write-up treats T3 as a smooth enough curve to differentiate twice, which is
    the point of the six-EMA cascade - a raw EMA's second difference is noise.
    Dividing by ATR makes the number comparable across symbols and regimes, so
    one threshold can be searched per symbol instead of a price-scale constant.
    """
    prev = np.roll(line, 1)
    prev[0] = line[0]
    prev2 = np.roll(line, 2)
    prev2[:2] = line[0]
    accel = np.zeros(line.size, dtype=np.float64)
    live = atr_series > 1e-12
    np.divide((line - prev) - (prev - prev2), atr_series, out=accel, where=live)
    return accel


def _resolve_conflicts(buy: np.ndarray, sell: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop bars where both sides fired; they cannot both be traded."""
    both = buy & sell
    return buy & ~both, sell & ~both


def _orb(cache: IndicatorCache, p: Params) -> Signals:
    """Opening range breakout, confirmed on the close.

    Research on index futures finds the first *confirmed* break of the opening
    range continues into the close roughly two thirds of the time, and that a
    close outside the range beats a wick touch by a wide margin. Only the first
    break of each session is taken.
    """
    close = cache.close
    t3, k, d, atr_series, adx_series = _common(cache, p)
    hi, lo, tradable = cache.opening_range(p.session_start_min, p.orb_minutes)
    htf_up, htf_down, allow_long, allow_short = _trend_gate(cache, p)
    regime = _regime(p, adx_series, close.size)

    buffer = atr_series * max(0.0, p.orb_buffer_atr)
    valid = tradable & np.isfinite(hi) & np.isfinite(lo) & regime
    up = valid & (close > np.nan_to_num(hi, nan=np.inf) + buffer) & allow_long
    down = valid & (close < np.nan_to_num(lo, nan=-np.inf) - buffer) & allow_short

    session = cache.session_id(p.session_start_min)

    if p.orb_retest:
        # Wait for price to break out, then pull back and reclaim the level
        # before entering - trades the retest instead of chasing the break.
        hi_level = np.nan_to_num(hi, nan=np.inf) + buffer
        lo_level = np.nan_to_num(lo, nan=-np.inf) - buffer
        broke_up_before = ind.any_before_in_group(up, session)
        broke_down_before = ind.any_before_in_group(down, session)
        near_hi = valid & (cache.low <= hi_level + atr_series * 0.5) & (close > hi_level) & allow_long
        near_lo = valid & (cache.high >= lo_level - atr_series * 0.5) & (close < lo_level) & allow_short
        up = near_hi & broke_up_before & ~up
        down = near_lo & broke_down_before & ~down

    buy = ind.first_per_group(up, session)
    sell = ind.first_per_group(down, session)
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _donchian(cache: IndicatorCache, p: Params) -> Signals:
    """Close beyond the prior N-bar channel, optionally only out of a squeeze.

    Unlike ORB this is not tied to a session open, so it catches expansions at
    any hour. Volatility compresses before it expands, so ``don_squeeze`` keeps
    entries to breaks that leave an unusually narrow channel - which is where
    breakout follow-through concentrates - instead of chasing an extended move.
    """
    close = cache.close
    t3, k, d, atr_series, adx_series = _common(cache, p)
    hi, lo, valid = cache.donchian(p.don_length)
    htf_up, htf_down, allow_long, allow_short = _trend_gate(cache, p)

    ok = valid & _regime(p, adx_series, close.size)
    if p.don_squeeze > 0:
        ok &= cache.squeeze_rank(p.don_length) <= p.don_squeeze
    if p.atr_pct_min > 0:
        ok &= cache.atr_rank(p.atr_period) >= p.atr_pct_min
    if p.min_body_ratio > 0:
        ok &= cache.body_ratio() >= p.min_body_ratio

    buffer = atr_series * max(0.0, p.don_buffer_atr)
    buy = ind.first_of_run(ok & (close > hi + buffer)) & allow_long
    sell = ind.first_of_run(ok & (close < lo - buffer)) & allow_short
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _vwap_rev(cache: IndicatorCache, p: Params) -> Signals:
    """Fade stretched distance from the session VWAP.

    Of the common VWAP strategies only mean reversion shows a statistically
    robust edge; crossovers show none. The edge concentrates when price is far
    from VWAP and is already turning back, and it evaporates on trend days,
    which is what ``adx_max`` guards against.
    """
    close, open_ = cache.close, cache.open
    t3, k, d, atr_series, adx_series = _common(cache, p)
    vwap, sd = cache.vwap(p.session_start_min)
    htf_up, htf_down, _, _ = _trend_gate(cache, p)
    regime = _regime(p, adx_series, close.size)

    band = sd * max(0.1, p.vwap_sd)
    stretched_up = close > vwap + band          # too far above -> sell
    stretched_dn = close < vwap - band          # too far below -> buy

    if p.vwap_reentry:
        # Only act once the bar itself is rolling back toward VWAP.
        stretched_up = stretched_up & (close < open_)
        stretched_dn = stretched_dn & (close > open_)

    warm = np.zeros(close.size, dtype=bool)
    warm[:] = sd > 0
    buy = stretched_dn & regime & warm
    sell = stretched_up & regime & warm

    if p.min_body_ratio > 0:
        body = cache.body_ratio()
        buy &= body >= p.min_body_ratio
        sell &= body >= p.min_body_ratio

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _t3_stoch(cache: IndicatorCache, p: Params) -> Signals:
    """T3 trend direction gated by a Stochastic RSI %K/%D cross.

    A long needs the T3 line turning up, %K crossing above %D from below, and the
    cross to happen before momentum is already exhausted. When the higher
    timeframe filter is on, the slower T3 must point the same way, which keeps
    the scalper from fading the dominant trend. Shorts are the mirror.
    """
    close = cache.close
    t3, k, d, atr_series, adx_series = _common(cache, p)

    t3_prev = np.roll(t3, 1)
    t3_prev[0] = t3[0]
    rising = t3 > t3_prev
    falling = t3 < t3_prev

    k_prev, d_prev = np.roll(k, 1), np.roll(d, 1)
    k_prev[0], d_prev[0] = k[0], d[0]
    bull_cross = (k_prev <= d_prev) & (k > d)
    bear_cross = (k_prev >= d_prev) & (k < d)

    hi_gate = STOCH_MID + p.stoch_band
    lo_gate = STOCH_MID - p.stoch_band
    upper = p.stoch_extreme
    lower = 100.0 - p.stoch_extreme

    regime = _regime(p, adx_series, close.size)
    htf_up, htf_down, trend_long, trend_short = _trend_gate(cache, p)

    buy = rising & bull_cross & (k < hi_gate) & (d < upper) & regime & trend_long
    sell = falling & bear_cross & (k > lo_gate) & (d > lower) & regime & trend_short

    if p.min_body_ratio > 0:
        # A signal bar that closed near its open is indecision, not an impulse.
        body = cache.body_ratio()
        strong = body >= p.min_body_ratio
        buy &= strong & (close >= cache.open)
        sell &= strong & (close <= cache.open)

    if p.atr_pct_min > 0:
        lively = cache.atr_rank(p.atr_period) >= p.atr_pct_min
        buy &= lively
        sell &= lively

    if p.t3_accel_min > 0:
        # "Rising" is a one-bar fact and half of those bars are the tail of a
        # move that is already decelerating. Requiring the T3 curve to still be
        # *bending* the trade's way keeps the entry on the building half.
        accel = _t3_accel(t3, atr_series)
        thr = float(p.t3_accel_min)
        buy &= accel >= thr
        sell &= accel <= -thr

    # The warmup window of the cascaded EMAs is meaningless; suppress it.
    warmup = min(close.size, max(p.t3_length * 6 * max(1, p.htf_factor),
                                 p.rsi_length + p.stoch_length + 10, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _squeeze_brk(cache: IndicatorCache, p: Params) -> Signals:
    """Bollinger/Keltner squeeze release, taken in the direction of momentum.

    The "squeeze" is on while the Bollinger Bands sit *inside* the Keltner
    Channel: standard deviation has fallen below the ATR envelope, which is the
    textbook signature of a compressed range. Volatility mean-reverts, so
    compression resolves into expansion; the release bar - the first bar where
    the bands push back outside the channel - is the trade. Direction is taken
    from the slope of a linear regression over the run-up rather than from the
    release bar itself, which is what separates this from chasing a candle.

    This is deliberately different from ``donchian``: Donchian breaks are about
    *price* leaving prior structure, this one is about *volatility* leaving a
    compressed state, and the two fire on different bars.
    """
    close = cache.close
    t3, k, d, atr_series, adx_series = _common(cache, p)
    _, bb_up, bb_dn = cache.bollinger(p.sqz_length, p.sqz_bb_sd)
    _, kc_up, kc_dn = cache.keltner(p.sqz_length, p.sqz_kc_atr)
    htf_up, htf_down, allow_long, allow_short = _trend_gate(cache, p)

    squeeze = (bb_up < kc_up) & (bb_dn > kc_dn)
    prev_sqz = np.roll(squeeze, 1)
    prev_sqz[0] = False
    fired = prev_sqz & ~squeeze                # first bar the compression lets go

    momentum = cache.slope(p.sqz_momentum_len)
    ok = fired & _regime(p, adx_series, close.size)
    if p.atr_pct_min > 0:
        ok &= cache.atr_rank(p.atr_period) >= p.atr_pct_min
    if p.min_body_ratio > 0:
        ok &= cache.body_ratio() >= p.min_body_ratio

    # The bands are meaningless until both have a full window behind them.
    warmup = min(close.size, max(p.sqz_length * 3, p.sqz_momentum_len * 2, p.atr_period * 3))
    ok[:warmup] = False

    buy = ok & (momentum > 0) & (close > cache.open) & allow_long
    sell = ok & (momentum < 0) & (close < cache.open) & allow_short
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _flow_rev(cache: IndicatorCache, p: Params) -> Signals:
    """Fade exhausted one-sided pressure using an OHLCV order-flow proxy.

    MT5 gives tick counts, not a tape, so aggressor side is inferred from where
    each bar closed inside its own range (close-location value) weighted by tick
    volume. Summed over a window and standardised, an extreme reading means one
    side has been leaning on the market hard - and the reliable part of that
    signal is not the push but its failure: with ``flow_divergence`` on, price
    must make a new extreme that the flow does *not* confirm, the classic
    absorption/divergence pattern. Reversion needs a non-trending tape, which is
    what ``adx_max`` enforces.
    """
    close = cache.close
    t3, k, d, atr_series, adx_series = _common(cache, p)
    run, z = cache.flow(p.flow_length)
    htf_up, htf_down, _, _ = _trend_gate(cache, p)
    regime = _regime(p, adx_series, close.size)

    lo_p, hi_p = ind.rolling_min_max(close, max(2, int(p.flow_length)))
    prev_hi = np.roll(hi_p, 1)
    prev_lo = np.roll(lo_p, 1)
    prev_hi[0], prev_lo[0] = hi_p[0], lo_p[0]

    thr = max(0.5, float(p.flow_z))
    # Buyers exhausted at the highs -> sell; sellers exhausted at the lows -> buy.
    cost_gate = cache.cost_ok(p.cost_rank_max)
    sell = regime & cost_gate & (z >= thr) & (close >= prev_hi)
    buy = regime & cost_gate & (z <= -thr) & (close <= prev_lo)

    if p.flow_divergence:
        run_prev = np.roll(run, 1)
        run_prev[0] = run[0]
        # New price extreme that flow refuses to confirm.
        sell &= run < run_prev
        buy &= run > run_prev

    if p.min_body_ratio > 0:
        body = cache.body_ratio()
        buy &= body >= p.min_body_ratio
        sell &= body >= p.min_body_ratio

    warmup = min(close.size, max(p.flow_length * 4, 220, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy = ind.first_of_run(buy)
    sell = ind.first_of_run(sell)
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _mtf_pullback(cache: IndicatorCache, p: Params) -> Signals:
    """Buy the dip inside a higher-timeframe uptrend (and the mirror).

    The other families all enter on an impulse; none of them waits. This one is
    the continuation trade: the higher timeframe must already be trending (that
    filter is mandatory here, not optional), price must then pull *against* that
    trend by at least ``pull_depth_atr`` ATR and reach the fast EMA, and the
    entry is the first bar that resumes in the trend direction. Buying a
    pullback rather than a breakout puts the stop behind recent structure
    instead of under an extended move, which is where the R:R of a scalp comes
    from.
    """
    close, open_ = cache.close, cache.open
    t3, k, d, atr_series, adx_series = _common(cache, p)
    fast = cache.ema(p.pull_fast)
    regime = _regime(p, adx_series, close.size)

    # The trend leg is required; without it there is no pullback to buy.
    factor = max(2, int(p.htf_factor) if p.htf_factor > 1 else 6)
    up, down = cache.htf(factor, p.t3_length, p.t3_volume_factor)
    htf_up, htf_down = up, down

    depth = atr_series * max(0.0, p.pull_depth_atr)
    window = max(2, int(p.pull_max_bars))
    swing_hi = ind.swing_highs(cache.high, window)
    swing_lo = ind.swing_lows(cache.low, window)

    # Pulled back far enough from the recent extreme *and* reached the fast EMA.
    dipped = (cache.low <= fast) & (swing_hi - cache.low >= depth)
    popped = (cache.high >= fast) & (cache.high - swing_lo >= depth)
    touched_dip = ind.rolling_sum(dipped.astype(np.float64), window) > 0
    touched_pop = ind.rolling_sum(popped.astype(np.float64), window) > 0

    resume_up = (close > open_) & (close > fast)
    resume_dn = (close < open_) & (close < fast)

    buy = up & regime & touched_dip & resume_up
    sell = down & regime & touched_pop & resume_dn

    if p.atr_pct_min > 0:
        lively = cache.atr_rank(p.atr_period) >= p.atr_pct_min
        buy &= lively
        sell &= lively
    if p.min_body_ratio > 0:
        body = cache.body_ratio()
        buy &= body >= p.min_body_ratio
        sell &= body >= p.min_body_ratio

    warmup = min(close.size, max(p.t3_length * 6 * factor, p.pull_fast * 5, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy = ind.first_of_run(buy)
    sell = ind.first_of_run(sell)
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _micro_rev(cache: IndicatorCache, p: Params) -> Signals:
    """Micro mean reversion whose entry threshold is measured in *cost*, not ATR.

    Every other family in this file asks "how far has price moved relative to
    its own volatility". That is the right question for a swing and the wrong
    one for a scalp: on an M5 bar the number that decides whether a reversion is
    worth taking is not ATR, it is the round-turn spread plus commission, and
    the ratio between the two is exactly what makes the same setup pay on gold
    and lose on EURUSD. So the displacement from a *fast* mean - ``mr_fast``
    bars, half an hour rather than a session - is divided by the real cost this
    trade will be charged, and the entry needs that quotient above
    ``mr_stretch_cost``. A five-cost stretch is worth fading; a one-cost stretch
    is noise you pay a spread to touch, whatever ATR says about it.

    On top of that sits the cost-regime gate: scalping profitability is decided
    at least as much by *when* you are willing to trade as by the signal, so
    ``cost_rank_max`` keeps entries to bars whose cost-to-range ratio sits in the
    cheaper part of its own recent distribution. Reversion also needs a
    two-sided tape, which is what ``adx_max`` is for.
    """
    close, open_ = cache.close, cache.open
    t3, k, d, atr_series, adx_series = _common(cache, p)
    htf_up, htf_down, _, _ = _trend_gate(cache, p)
    regime = _regime(p, adx_series, close.size)

    cost = cache.cost()
    if cost is None:
        # No honest cost series -> this family has nothing to measure against.
        dead = np.zeros(close.size, dtype=bool)
        return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series,
                       buy=dead, sell=dead, htf_up=htf_up, htf_down=htf_down)

    mean = cache.ema(max(2, int(p.mr_fast)))
    priced = cost > 0
    stretch = np.zeros(close.size, dtype=np.float64)
    np.divide(np.abs(close - mean), cost, out=stretch, where=priced)

    far = priced & (stretch >= max(1.0, float(p.mr_stretch_cost)))
    ok = far & regime & cache.cost_ok(p.cost_rank_max)

    sell = ok & (close > mean)
    buy = ok & (close < mean)
    if p.mr_confirm:
        # The bar itself must already be rolling back toward the mean.
        sell = sell & (close < open_)
        buy = buy & (close > open_)

    if p.min_body_ratio > 0:
        body = cache.body_ratio()
        buy &= body >= p.min_body_ratio
        sell &= body >= p.min_body_ratio
    if p.atr_pct_min > 0:
        lively = cache.atr_rank(p.atr_period) >= p.atr_pct_min
        buy &= lively
        sell &= lively

    warmup = min(close.size, max(p.mr_fast * 6, 260, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy = ind.first_of_run(buy)
    sell = ind.first_of_run(sell)
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _burst(cache: IndicatorCache, p: Params) -> Signals:
    """Continuation off a single range-expansion bar that closed on its extreme.

    The existing breakout families both key off *levels*: ORB off the session's
    opening range, Donchian off an N-bar channel. Neither of them can fire on
    the bar that actually matters to a scalper - the one where a burst of
    one-sided activity expands the range well beyond what the last hour has been
    doing and then closes hard against its own extreme, with no prior level
    involved. That bar is the signal here: range above ``brst_range_z`` standard
    deviations of the trailing range distribution, close inside the top (or
    bottom) ``brst_close_pct`` of its own bar, entry on the continuation.

    Because it is anchored to nothing but the current bar it is available at any
    hour, which is the point on M5 - and because a burst is exactly when spreads
    widen, it carries the same ``cost_rank_max`` regime gate as ``micro_rev``:
    an expansion bar you have to pay up for is not an edge.
    """
    close, open_ = cache.close, cache.open
    t3, k, d, atr_series, adx_series = _common(cache, p)
    htf_up, htf_down, allow_long, allow_short = _trend_gate(cache, p)
    regime = _regime(p, adx_series, close.size)

    window = max(5, int(p.brst_lookback))
    span = cache.high - cache.low
    mean = ind.sma(span, window)
    sd = ind.rolling_std(span, window)
    expansion = span >= mean + max(0.0, float(p.brst_range_z)) * sd

    # Where the bar closed inside its own range: 1.0 is a close on the high.
    clv = np.zeros(close.size, dtype=np.float64)
    wide = span > 1e-12
    np.divide(close - cache.low, span, out=clv, where=wide)

    edge = min(0.99, max(0.5, float(p.brst_close_pct)))
    ok = expansion & wide & regime & cache.cost_ok(p.cost_rank_max)
    if p.atr_pct_min > 0:
        ok &= cache.atr_rank(p.atr_period) >= p.atr_pct_min

    buy = ok & (clv >= edge) & (close > open_) & allow_long
    sell = ok & (clv <= 1.0 - edge) & (close < open_) & allow_short

    warmup = min(close.size, max(window * 4, 260, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy = ind.first_of_run(buy)
    sell = ind.first_of_run(sell)
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _t3_ribbon(cache: IndicatorCache, p: Params) -> Signals:
    """Fast Tillson T3 crossing a slow Tillson T3 - the cross *is* the entry.

    ``t3_stoch`` only ever asks T3 a yes/no question ("is it rising?") and lets
    a Stochastic RSI pick the bar. That throws away what T3 is actually good at:
    it is a low-lag curve, so the *relationship between two of them* carries
    real information the way a moving-average ribbon does, but without the lag
    that makes an EMA ribbon useless on M5. Fast above slow is the bias, the
    crossover bar is the trigger (the classic golden/death cross read of a T3
    pair), and because both lines are six-EMA cascades the cross is far less
    prone to the whipsaw that kills a plain MA cross.

    Two curvature-aware filters sit on top, and both are searched rather than
    assumed. ``t3_slope_atr`` requires the slow line to already be travelling at
    a minimum speed in ATR units, which throws away crosses that happen inside a
    flat ribbon - where a T3 pair braids and every cross is noise. ``t3_accel_min``
    requires the fast line to still be bending the trade's way, which is the
    difference between joining a move and joining its exhaustion.
    """
    close = cache.close
    t3, k, d, atr_series, adx_series = _common(cache, p)
    htf_up, htf_down, allow_long, allow_short = _trend_gate(cache, p)
    regime = _regime(p, adx_series, close.size)

    fast_len = max(2, int(p.t3_fast))
    slow_len = max(fast_len + 1, int(round(fast_len * max(1.2, float(p.t3_slow_mult)))))
    # Each line gets its own volume factor when the search asks for one. vf is a
    # curvature knob, not a second length: a shorter line damped differently is a
    # genuinely different curve, which is exactly what the Tillson scalping
    # template does (8/0.7 against 5/0.618). 0 inherits and stays backward
    # compatible with the single-vf ribbon.
    fast_vf = float(p.t3_fast_vf) if float(p.t3_fast_vf) > 0 else float(p.t3_volume_factor)
    fast = cache.t3(fast_len, fast_vf)
    slow = cache.t3(slow_len, p.t3_volume_factor)

    fast_prev, slow_prev = np.roll(fast, 1), np.roll(slow, 1)
    fast_prev[0], slow_prev[0] = fast[0], slow[0]
    cross_up = (fast_prev <= slow_prev) & (fast > slow)
    cross_dn = (fast_prev >= slow_prev) & (fast < slow)

    # Speed of the slow line per bar, in ATR - scale free across symbols.
    slope = np.zeros(close.size, dtype=np.float64)
    live = atr_series > 1e-12
    np.divide(slow - slow_prev, atr_series, out=slope, where=live)
    thr = max(0.0, float(p.t3_slope_atr))

    ok = regime & live & cache.cost_ok(p.cost_rank_max)
    if p.atr_pct_min > 0:
        ok &= cache.atr_rank(p.atr_period) >= p.atr_pct_min
    if p.min_body_ratio > 0:
        ok &= cache.body_ratio() >= p.min_body_ratio

    buy = ok & cross_up & (close > fast) & allow_long
    sell = ok & cross_dn & (close < fast) & allow_short
    # 0 (the default) means disabled, same convention as every other
    # optional filter in this family (t3_accel_min, st_mult, cost_rank_max,
    # don_squeeze, adx_max - all gated behind `if p.x > 0`). This one was
    # applied unconditionally instead: thr=0.0 still demanded slope>=0.0/
    # -slope>=0.0, permanently vetoing a cross that fires while the slow
    # line is momentarily flat or still pointed the other way - often the
    # earliest, most valuable part of the move, and exactly the case the
    # "0 disables" doc comment above promised would be let through.
    if thr > 0:
        buy &= slope >= thr
        sell &= -slope >= thr

    if p.t3_accel_min > 0:
        accel = _t3_accel(fast, atr_series)
        acc_thr = float(p.t3_accel_min)
        buy &= accel >= acc_thr
        sell &= accel <= -acc_thr

    warmup = min(close.size, max(slow_len * 6 * max(1, p.htf_factor if p.htf_mode == "t3" else 1),
                                 slow_len * 8, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _dual_t3(cache: IndicatorCache, p: Params) -> Signals:
    """Two Tillson T3 lines and nothing else. The cross IS the entry.

    This is the deliberately minimal core of the system: a fast T3 crossing a
    slow T3 decides direction and timing, and ATR decides everything about risk
    (the hard stop and the trail - shared with every other family, none of it
    reinvented here). There is no Stochastic RSI, no RSI, no
    ADX regime gate, no higher-timeframe agreement gate, no Bollinger/Keltner
    squeeze, no order-flow volume proxy, no Fibonacci ratio, no body-ratio or
    ATR-percentile entry filter. Those series are not merely disabled here, they
    are never computed for this family.

    The one optional layer is SuperTrend (``st_mult > 0``), and it is admitted
    only because it is itself an ATR construction - an ATR envelope around the
    bar midpoint that ratchets toward price - so it says nothing the T3 + ATR
    vocabulary cannot already say. When it is on, its direction must agree with
    the cross; when it is off (the default, and the grid is allowed to keep it
    off) the cross stands alone. Whether it earns its place is decided by the
    walk-forward, not by taste.

    Portfolio safety rails - session windows, spread sanity, cooldown, the daily
    loss halt, the supervisor - all still apply at the engine level. They are
    not indicators and stripping the signal does not strip them.
    """
    close = cache.close
    size = close.size
    # T3 and ATR only. k/d/adx are UI display slots; this family leaves them at
    # zero rather than computing a Stochastic RSI it does not use.
    t3 = cache.t3(p.t3_length, p.t3_volume_factor)
    atr_series = cache.atr(p.atr_period)
    zeros = np.zeros(size, dtype=np.float64)
    flat = np.zeros(size, dtype=bool)

    fast_len = max(2, int(p.t3_fast))
    slow_len = max(fast_len + 1, int(round(fast_len * max(1.2, float(p.t3_slow_mult)))))
    # A T3's volume factor is a curvature knob, not a second length, so the two
    # lines may be damped differently. 0 inherits the slow line's factor.
    fast_vf = float(p.t3_fast_vf) if float(p.t3_fast_vf) > 0 else float(p.t3_volume_factor)
    fast = cache.t3(fast_len, fast_vf)
    slow = cache.t3(slow_len, p.t3_volume_factor)

    fast_prev, slow_prev = np.roll(fast, 1), np.roll(slow, 1)
    fast_prev[0], slow_prev[0] = fast[0], slow[0]
    buy = (fast_prev <= slow_prev) & (fast > slow)
    sell = (fast_prev >= slow_prev) & (fast < slow)

    if float(p.st_mult) > 0:
        direction = cache.supertrend(p.st_period, p.st_mult)
        buy = buy & (direction > 0)
        sell = sell & (direction < 0)

    # Same two optional gates every other family already has (adx_min/adx_max,
    # atr_pct_min) - not new indicators, just the existing regime/volatility
    # vocabulary made available to this family too, off by default.
    need_adx = p.adx_min > 0 or p.adx_max > 0
    adx_series = cache.adx(p.adx_period) if need_adx else zeros
    if need_adx:
        ok = _regime(p, adx_series, size)
        buy &= ok
        sell &= ok
    if p.atr_pct_min > 0:
        lively = cache.atr_rank(p.atr_period) >= p.atr_pct_min
        buy &= lively
        sell &= lively

    # The cascaded EMAs are meaningless until the slow line has a full cascade
    # behind it; the ATR the exits are sized from needs its own warmup too.
    warmup = min(size, max(slow_len * 8, p.atr_period * 3,
                           int(p.st_period) * 3 if float(p.st_mult) > 0 else 0,
                           p.adx_period * 4 if need_adx else 0))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=zeros, d=zeros, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=flat, htf_down=flat)


def _st_trend(cache: IndicatorCache, p: Params) -> Signals:
    """SuperTrend flip: one indicator that is entry, direction and trail in one.

    The entry is the bar on which the SuperTrend line changes side - the close
    breaks the active ATR band, the band jumps to the other side of price, and
    that flip *is* the trend inception. Nothing is stacked on top of it: no T3,
    no Stochastic RSI, no higher-timeframe agreement, no order-flow proxy, no
    body-ratio or ATR-percentile screen. Those series are never computed here.

    Why this signal rather than a moving-average cross: a cross fires on every
    wobble of two smoothed lines, so in a flat market it fires constantly and
    each fire is a fresh trade. SuperTrend has hysteresis built into it - once
    it is long, price has to close a full ``st_mult * ATR`` band below the
    ratcheted low band before it will go short - so a range that never travels
    that distance produces *no* signal at all instead of a stream of them. That
    is the structural answer to the flat-market whipsaw a crossover family
    cannot dodge, and it is the reason this family is paired with a no-target,
    trail-only exit: the same ATR band that admitted the trade is the shape the
    trailing stop is trying to follow out of it.

    The one permitted regime gate is ADX (``adx_min``, 0 disables and the grid
    is free to keep it off). It is a single scalar threshold on trend strength,
    not a second signal - it can only veto a flip, never create one.

    Exits are the shared ATR mechanics, and there is only one set of them: a
    hard ATR stop opens the trade and the ATR trail is the only thing that
    closes a winner. Nothing here is special-cased - every family gets that
    same exit - but it is the exit this entry was built for.
    """
    close = cache.close
    size = close.size
    atr_series = cache.atr(p.atr_period)
    zeros = np.zeros(size, dtype=np.float64)
    flat = np.zeros(size, dtype=bool)

    period = max(2, int(p.st_period))
    # Unlike dual_t3 - where SuperTrend is an optional confirmation and 0 turns
    # it off - here it is the whole signal, so a zero/negative multiple would
    # leave nothing to trade. Clamp to a usable floor instead.
    mult = max(0.5, float(p.st_mult) if float(p.st_mult) > 0 else 2.0)
    direction = cache.supertrend(period, mult)
    prev = np.roll(direction, 1)
    prev[0] = direction[0]
    buy = (direction > 0) & (prev <= 0)
    sell = (direction < 0) & (prev >= 0)

    need_adx = p.adx_min > 0 or p.adx_max > 0
    adx_series = cache.adx(p.adx_period) if need_adx else zeros
    if need_adx:
        ok = _regime(p, adx_series, size)
        buy &= ok
        sell &= ok

    # Wilder's ATR needs its own cascade before the bands mean anything, and the
    # ratcheting line needs a run of bars before its level is history-driven
    # rather than seed-driven.
    warmup = min(size, max(period * 10, p.atr_period * 3,
                           p.adx_period * 4 if need_adx else 0))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    # ``t3`` is a UI display slot; this family computes no T3 of its own, so the
    # SuperTrend line's own direction is reported instead of a series it never
    # looked at.
    return Signals(t3=direction.astype(np.float64), k=zeros, d=zeros, atr=atr_series,
                   adx=adx_series, buy=buy, sell=sell, htf_up=flat, htf_down=flat)


def _t3_flip(cache: IndicatorCache, p: Params) -> Signals:
    """ONE Tillson T3 line. The line's own direction change IS the entry.

    This is the smallest T3 rule that exists, and it is deliberately not any of
    the three T3 families already in this file. ``t3_stoch`` only asks the line a
    yes/no question ("is it rising?") and lets a Stochastic RSI pick the bar;
    ``t3_ribbon`` and ``dual_t3`` both need a *second* line and trade the
    crossover. Here there is no second line and no second indicator: the bar on
    which the single line stops falling and starts rising is the long, the bar on
    which it stops rising and starts falling is the short. That is exactly the
    green/red line a T3 is drawn as on a chart, traded literally.

    Why that is worth measuring on its own: a crossover of two smoothed lines is
    a *lagged* read of the same turn this fires on - the fast line has to travel
    far enough past the slow one before the cross registers, which on M5 costs
    several bars of the move and, when the two lines are braided in a range,
    manufactures crosses the underlying curve never justified. The direction
    change is the earliest honest statement the curve can make about itself, and
    T3's six-EMA cascade is smooth enough that a one-bar direction change is a
    real turn rather than the tick noise a raw EMA's slope would report.

    Nothing else is computed for this family - no Stochastic RSI, no ADX, no
    higher-timeframe agreement, no order-flow proxy, no Bollinger/Keltner, no
    body-ratio or ATR-percentile screen, no SuperTrend, no second T3. Those
    series are not "disabled", they are never built.

    The single optional layer is ``t3_accel_min`` (0 disables, and the grid is
    free to keep it off), which answers the one weakness this signal genuinely
    has: in a flat market the line still wiggles, and every wiggle is a flip. The
    curvature of the line at the flip bar - its second difference, normalised by
    ATR - is how hard that turn actually was. It is not a new indicator: it is
    the same line's own derivative, so the family stays a single-T3 read, and it
    can only veto a flip, never create one. Whether it is worth its place is
    decided by the walk-forward per symbol, not assumed here.

    Exits are the shared ATR mechanics: a hard ATR stop at entry and the ATR
    trail as the only way out of a winner. That suits a direction-change entry
    particularly well - it has no level to aim at; it either keeps curving or
    it flips back.
    """
    close = cache.close
    size = close.size
    # T3 and ATR only. k/d/adx are UI display slots; this family leaves them at
    # zero rather than computing series it never reads.
    t3 = cache.t3(p.t3_length, p.t3_volume_factor)
    atr_series = cache.atr(p.atr_period)
    zeros = np.zeros(size, dtype=np.float64)
    flat = np.zeros(size, dtype=bool)

    prev = np.roll(t3, 1)
    prev[0] = t3[0]
    rising = t3 > prev
    falling = t3 < prev
    # A flip is a *transition*: the previous bar has to have been going the other
    # way, otherwise every bar of a trend would be an entry.
    was_rising = np.roll(rising, 1)
    was_falling = np.roll(falling, 1)
    was_rising[0] = False
    was_falling[0] = False
    buy = rising & ~was_rising
    sell = falling & ~was_falling

    if p.t3_accel_min > 0:
        # At a flip bar the second difference always has the trade's sign (the
        # line changed direction), so this is a magnitude gate, not a direction
        # one: it throws away the shallow turns a flat market is made of and
        # keeps the ones with real curvature behind them.
        accel = _t3_accel(t3, atr_series)
        thr = float(p.t3_accel_min)
        buy &= accel >= thr
        sell &= accel <= -thr

    # Six cascaded EMAs are meaningless until the cascade has filled, and the
    # ATR the exits are sized from needs its own warmup.
    warmup = min(size, max(p.t3_length * 8, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=zeros, d=zeros, atr=atr_series, adx=zeros, buy=buy, sell=sell,
                   htf_up=flat, htf_down=flat)


def _macd_flip(cache: IndicatorCache, p: Params) -> Signals:
    """MACD histogram zero-cross - the same edge-trigger idea as ``t3_flip``,
    read off genuinely different information.

    ``t3_flip`` asks "did this one smoothed price line just change direction?"
    MACD's histogram is the *spread* between a fast and a slow EMA of price -
    a momentum-divergence read, not a price-smoothing read. Two EMAs pulling
    apart or converging can flip sign before a single slower line's own slope
    does, and it can also stay flat through a chop a single line would still
    wiggle across. It is not a T3 variant wearing a different name: nothing
    about it is derived from the T3 cascade or its source series.

    Same discipline as t3_flip: the histogram crossing zero is the whole
    signal, no state, no filter menu. The entry is the transition bar only
    (was on the other side of zero last bar), never every bar the histogram
    happens to sit positive or negative - that is a trend-following state,
    not a flip.

    Exits are the shared ATR mechanics, same as every other family here -
    this adds a signal, not a new exit model.
    """
    close = cache.close
    size = close.size
    _, _, hist = cache.macd(p.macd_fast, p.macd_slow, p.macd_signal)
    atr_series = cache.atr(p.atr_period)
    zeros = np.zeros(size, dtype=np.float64)
    flat = np.zeros(size, dtype=bool)

    above = hist > 0
    below = hist < 0
    was_above = np.roll(above, 1)
    was_below = np.roll(below, 1)
    was_above[0] = False
    was_below[0] = False
    buy = above & ~was_above
    sell = below & ~was_below

    # MACD needs the slow EMA plus its own signal EMA to settle, and the ATR
    # the exits are sized from needs its own warmup.
    warmup = min(size, max(p.macd_slow + p.macd_signal, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=zeros, k=zeros, d=zeros, atr=atr_series, adx=zeros, buy=buy, sell=sell,
                   htf_up=flat, htf_down=flat)


def _wavetrend_flip(cache: IndicatorCache, p: Params) -> Signals:
    """WaveTrend wt1/wt2 crossover - a third, independent flip read.

    ``t3_flip`` reads a smoothed price line's own direction. ``macd_flip``
    reads the spread of two same-input EMAs. This reads price normalised
    against its own mean absolute deviation from a smoothed typical price -
    a bounded, volatility-relative oscillator rather than a raw price-unit
    spread, so its crossovers are on a comparable scale across symbols and
    regimes instead of needing per-symbol re-scaling.

    Same rule as the other two flip families: wt1 crossing wt2 is the whole
    entry, transition bar only, no state, no filter menu, no zone (the
    classic +-60/100 overbought/oversold read is a different, separately
    justified strategy and not bolted on here).
    """
    close = cache.close
    size = close.size
    wt1, wt2 = cache.wavetrend(p.wt_channel_len, p.wt_avg_len)
    atr_series = cache.atr(p.atr_period)
    zeros = np.zeros(size, dtype=np.float64)
    flat = np.zeros(size, dtype=bool)

    above = wt1 > wt2
    below = wt1 < wt2
    was_above = np.roll(above, 1)
    was_below = np.roll(below, 1)
    was_above[0] = False
    was_below[0] = False
    buy = above & ~was_above
    sell = below & ~was_below

    warmup = min(size, max(p.wt_channel_len * 8, p.wt_avg_len * 4, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=zeros, k=zeros, d=zeros, atr=atr_series, adx=zeros, buy=buy, sell=sell,
                   htf_up=flat, htf_down=flat)


def _stoch_flip(cache: IndicatorCache, p: Params) -> Signals:
    """Slow Stochastic %K/%D crossover - a fourth, independent flip read.

    Not ``t3_stoch`` wearing a different name: ``t3_stoch`` runs a Stochastic
    calculation *on RSI values* (StochRSI) as a yes/no gate alongside a T3
    line, and the T3 line's own direction still picks the bar. This measures
    where the close sits inside its own recent high/low range directly - RSI
    is never computed - and the %K/%D crossover *is* the entry, with no T3
    line involved at all. Genuinely different information: RSI reads
    average gain/loss momentum, raw Stochastic reads range position.

    Same discipline as the other flip families: the crossover bar is the
    whole signal, transition only, no zone read (classic <20/>80
    overbought/oversold is a different, separately justified strategy).
    """
    close = cache.close
    size = close.size
    k, d = cache.stoch_slow(p.stoch_k_period, p.stoch_k_smooth, p.stoch_d_smooth)
    atr_series = cache.atr(p.atr_period)
    zeros = np.zeros(size, dtype=np.float64)
    flat = np.zeros(size, dtype=bool)

    above = k > d
    below = k < d
    was_above = np.roll(above, 1)
    was_below = np.roll(below, 1)
    was_above[0] = False
    was_below[0] = False
    buy = above & ~was_above
    sell = below & ~was_below

    warmup = min(size, max(p.stoch_k_period * 4, (p.stoch_k_smooth + p.stoch_d_smooth) * 8,
                           p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=zeros, k=k, d=d, atr=atr_series, adx=zeros, buy=buy, sell=sell,
                   htf_up=flat, htf_down=flat)


def _parabolic_flip(cache: IndicatorCache, p: Params) -> Signals:
    """Parabolic SAR side flip - a fifth, independent flip read.

    Same family shape as ``st_trend`` (a trailing band whose own side change
    is the entry) but a genuinely different band: SuperTrend's width is a
    fixed ATR multiple, SAR's is its own accelerating step toward the last
    extreme - it tightens the longer a trend runs, so it can flip on a
    shallower pullback late in a move than an ATR band of fixed width would.
    """
    close = cache.close
    size = close.size
    atr_series = cache.atr(p.atr_period)
    zeros = np.zeros(size, dtype=np.float64)
    flat = np.zeros(size, dtype=bool)

    direction = cache.psar(p.psar_af_step, p.psar_af_max)
    prev = np.roll(direction, 1)
    prev[0] = direction[0]
    buy = (direction > 0) & (prev <= 0)
    sell = (direction < 0) & (prev >= 0)

    warmup = min(size, max(30, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=direction.astype(np.float64), k=zeros, d=zeros, atr=atr_series, adx=zeros,
                   buy=buy, sell=sell, htf_up=flat, htf_down=flat)


def _trix_flip(cache: IndicatorCache, p: Params) -> Signals:
    """TRIX zero-cross - the slow, triple-smoothed counterpart to the fast
    flip families (t3_flip, macd_flip, wavetrend_flip, stoch_flip, st_trend,
    parabolic_flip all react within a handful of bars; TRIX's three EMA
    passes cost real lag on purpose, in exchange for filtering out the chop
    those fast reads all still catch).

    The line crossing zero (momentum turning from decelerating to
    accelerating, or vice versa) is the entry - transition bar only, same
    discipline as every other flip family here.
    """
    close = cache.close
    size = close.size
    line = cache.trix(p.trix_length)
    atr_series = cache.atr(p.atr_period)
    zeros = np.zeros(size, dtype=np.float64)
    flat = np.zeros(size, dtype=bool)

    above = line > 0
    below = line < 0
    was_above = np.roll(above, 1)
    was_below = np.roll(below, 1)
    was_above[0] = False
    was_below[0] = False
    buy = above & ~was_above
    sell = below & ~was_below

    warmup = min(size, max(p.trix_length * 12, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=zeros, k=zeros, d=zeros, atr=atr_series, adx=zeros, buy=buy, sell=sell,
                   htf_up=flat, htf_down=flat)


def _aroon_flip(cache: IndicatorCache, p: Params) -> Signals:
    """Aroon oscillator zero-cross - a seventh, independent flip read.

    Every other family here reads a price level, a spread between two
    series, or a deviation-normalised oscillator. Aroon reads none of that -
    it is purely *how many bars since the last high/low extreme*, so it can
    tell a trend that just printed a fresh extreme (pinned near +-100) apart
    from one that has been drifting with no new extreme in a while (drifting
    toward zero) even when price itself looks similar on both.
    """
    close = cache.close
    size = close.size
    osc = cache.aroon(p.aroon_length)
    atr_series = cache.atr(p.atr_period)
    zeros = np.zeros(size, dtype=np.float64)
    flat = np.zeros(size, dtype=bool)

    above = osc > 0
    below = osc < 0
    was_above = np.roll(above, 1)
    was_below = np.roll(below, 1)
    was_above[0] = False
    was_below[0] = False
    buy = above & ~was_above
    sell = below & ~was_below

    warmup = min(size, max(p.aroon_length * 3, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=zeros, k=zeros, d=zeros, atr=atr_series, adx=zeros, buy=buy, sell=sell,
                   htf_up=flat, htf_down=flat)


def _liq_sweep(cache: IndicatorCache, p: Params) -> Signals:
    """Liquidity sweep reversal: a wick past recent swing structure, rejected.

    A stop-hunt/liquidity-sweep entry is a pure price-action idea with no
    indicator behind it: retail stops cluster just past the last swing
    high/low, and a bar that wicks through that level and then closes back on
    the other side has swept those stops and failed to hold the break - the
    classic false-break reversal. The swing level is the same causal
    swing_highs/swing_lows the structure-based trailing stop already uses, so
    this reuses the existing definition of "recent structure" rather than
    inventing a second one. ``swp_wick_atr`` keeps the sweep to a real
    excursion (in ATR units) rather than a single point of noise, and the
    close must fully reclaim the level - a bar that wicks *and* closes past it
    is a breakout continuing, not a sweep.
    """
    close = cache.close
    t3, k, d, atr_series, adx_series = _common(cache, p)
    htf_up, htf_down, _, _ = _trend_gate(cache, p)
    regime = _regime(p, adx_series, close.size)

    lookback = max(3, int(p.swp_lookback))
    swing_hi = ind.swing_highs(cache.high, lookback)
    swing_lo = ind.swing_lows(cache.low, lookback)
    wick = atr_series * max(0.0, p.swp_wick_atr)

    # Swept the high and failed to hold above it -> sell.
    sell = (cache.high > swing_hi + wick) & (close < swing_hi) & regime
    # Swept the low and failed to hold below it -> buy.
    buy = (cache.low < swing_lo - wick) & (close > swing_lo) & regime

    if p.min_body_ratio > 0:
        body = cache.body_ratio()
        buy &= body >= p.min_body_ratio
        sell &= body >= p.min_body_ratio
    if p.atr_pct_min > 0:
        lively = cache.atr_rank(p.atr_period) >= p.atr_pct_min
        buy &= lively
        sell &= lively

    # The swing lookback needs a real window of bars behind it before its
    # "recent high/low" means anything.
    warmup = min(close.size, max(lookback * 4, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy = ind.first_of_run(buy)
    sell = ind.first_of_run(sell)
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


_FAMILIES = {
    "t3_stoch": _t3_stoch,
    "orb": _orb,
    "vwap_rev": _vwap_rev,
    "donchian": _donchian,
    "squeeze_brk": _squeeze_brk,
    "flow_rev": _flow_rev,
    "mtf_pullback": _mtf_pullback,
    "micro_rev": _micro_rev,
    "burst": _burst,
    "t3_ribbon": _t3_ribbon,
    "dual_t3": _dual_t3,
    "st_trend": _st_trend,
    "t3_flip": _t3_flip,
    "liq_sweep": _liq_sweep,
    "macd_flip": _macd_flip,
    "wavetrend_flip": _wavetrend_flip,
    "stoch_flip": _stoch_flip,
    "parabolic_flip": _parabolic_flip,
    "trix_flip": _trix_flip,
    "aroon_flip": _aroon_flip,
}


def required_bars(p: Params) -> int:
    """Lookback needed before the indicator stack is trustworthy."""
    htf = max(1, p.htf_factor if p.htf_mode == "t3" else 1)
    if p.strategy == "mtf_pullback":
        htf = max(htf, 6)            # the trend leg is mandatory for this family
    breakout = p.don_length * 4 + (240 if p.don_squeeze > 0 else 0)
    return int(max(400, p.t3_length * 20 * htf,
                   (p.rsi_length + p.stoch_length + p.smooth_k + p.smooth_d) * 8,
                   p.atr_period * 10, p.adx_period * 10, breakout,
                   p.sqz_length * 6, p.sqz_momentum_len * 4,
                   p.flow_length * 6 + 240, p.pull_fast * 10,
                   # The scalping families rank cost against a 240-bar window.
                   p.mr_fast * 8 + 260, p.brst_lookback * 6 + 260,
                   # The ribbon's slow line is a cascade over t3_fast * mult.
                   int(p.t3_fast * max(1.2, p.t3_slow_mult)) * 20,
                   int(p.st_period) * 10
                   if (p.st_mult > 0 or p.strategy == "st_trend") else 0,
                   p.swp_lookback * 4,
                   (p.macd_slow + p.macd_signal) * 10,
                   (p.wt_channel_len + p.wt_avg_len) * 10,
                   (p.stoch_k_period + p.stoch_k_smooth + p.stoch_d_smooth) * 8,
                   p.trix_length * 15,
                   p.aroon_length * 8))
