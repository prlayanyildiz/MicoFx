from __future__ import annotations

import ast
import functools
import inspect
import textwrap
from dataclasses import dataclass
from typing import Any

import numpy as np

from . import indicators as ind
from .logbus import LOG
from .models import EXIT_RISK_FIELDS, OPT_FIELDS, SymbolConfig

# Optional compute gates. 0 disables each. When a family starts reading them,
# leftover panel values from a previous family must not bind unless the last
# apply stamp named them (see Params.from_config).
_UNSTAMPED_GATES = (
    "htf_factor", "adx_min", "adx_max", "min_body_ratio", "atr_pct_min",
    "cost_rank_max",
)
_ABSENT_GATE_ZERO = frozenset(
    ("adx_min", "adx_max", "min_body_ratio", "atr_pct_min"))
# These three just started reading HTF/ADX. Leftover numbers from a previous
# family were never in their apply stamp (28.08 Brent/NAS). dual_t3/burst
# already read the same dials; an omitted stamp key there is the live row
# (GER40 adx_min=15), not a leftover to wipe.
_GATED_FLIPS = frozenset()

# mtf_pullback: a shallower dip is index noise, not a pullback. Search used
# to offer 0.3; NAS100 live (27.08) paid 22 SL of 34 closes on that value.
MIN_PULL_DEPTH_ATR = 0.5


@dataclass
class Params:
    """Flat parameter view so the optimizer can vary values without a full config."""

    strategy: str = "mtf_pullback"

    # ---- higher-timeframe trend pullback ----
    pull_fast: int = 8
    pull_depth_atr: float = 0.5
    pull_max_bars: int = 6
    pull_break_confirm: float = 0.0   # 0 = off; 1 = resume bar must break prior bar extreme

    # ---- range-expansion momentum burst (M5-native scalp) ----
    brst_lookback: int = 20
    brst_range_z: float = 1.5
    brst_close_pct: float = 0.7

    # ---- N-bar channel break (channel_break) ----
    chan_lookback: int = 50
    chan_buffer_atr: float = 0.0

    # ---- adaptive cost-regime gate (burst) ----
    cost_rank_max: float = 0.0       # 0 disables; percentile ceiling on cost/range

    # ---- reversion regime ceiling (_regime) ----
    adx_max: float = 0.0             # 0 disables; reversion dies in strong trends

    t3_length: int = 6
    t3_volume_factor: float = 0.7
    rsi_length: int = 9
    stoch_length: int = 9
    smooth_k: int = 3
    smooth_d: int = 3
    stoch_extreme: float = 80.0
    htf_factor: int = 6
    htf_mode: str = "t3"
    atr_period: int = 14
    adx_period: int = 14
    adx_min: float = 0.0
    # Exit model: hard ATR stop + ATR trail. Scale-out overlay is
    # partial_at_r (0 = off); live lot is derived, paper frac 0 = same third.
    sl_atr_mult: float = 1.2
    trail_start_atr: float = 0.8
    trail_step_atr: float = 0.6
    trail_mode: str = "atr"          # "atr" | "structure" | "hybrid"
    trail_lookback: int = 5          # bars to look back for swing high/low (structure/hybrid)
    breakeven_at_r: float = 0.0      # 0 = off; lock SL at entry after this many R
    partial_at_r: float = 0.0        # 0 = off; paper scale-out rung in R
    partial_close_frac: float = 0.0  # 0 = off; fraction booked at the rung
    harvest_at_r: float = 0.0        # 0 = off; tighten trail after this many R
    harvest_step_atr: float = 0.0    # 0 = off; ATR distance once harvest_at_r hits
    cooldown_sec: int = 0            # live engine caps to 2 bars of TF; BT mirrors that
    max_spread_atr: float = 0.0
    min_atr_ratio: float = 0.0
    min_body_ratio: float = 0.0
    atr_pct_min: float = 0.0

    @classmethod
    def from_config(cls, cfg: SymbolConfig, **overrides: Any) -> Params:
        base = {f: getattr(cfg, f) for f in cls.__dataclass_fields__ if hasattr(cfg, f)}
        # A real apply stamp lists the OPT axes that search chose. Leftover
        # htf/adx from a previous family must not start gating the new one
        # (28.08 Brent stoch_flip still carried dual_t3's 15-25 ADX).
        stamped = (getattr(cfg, "opt_summary", None) or {}).get("params")
        if isinstance(stamped, dict) and stamped:
            base.update(unstamped_gates_to_zero(
                str(base.get("strategy") or ""), stamped))
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
                self.stoch_length, self.smooth_k, self.smooth_d,
                self.stoch_extreme, self.atr_period, self.adx_period, self.adx_min,
                self.adx_max, self.htf_factor, self.htf_mode, self.min_body_ratio,
                self.atr_pct_min,
                self.pull_fast, self.pull_depth_atr, self.pull_max_bars,
                self.pull_break_confirm,
                self.brst_lookback, self.brst_range_z, self.brst_close_pct,
                self.chan_lookback, self.chan_buffer_atr,
                self.cost_rank_max)


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
        self._body: np.ndarray | None = None
        self._ema: dict[int, np.ndarray] = {}
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
            # filter exists to catch. burst used to get an all-pass instead,
            # which turned a real cost gate into a no-op exactly when it
            # mattered.
            return np.zeros(size, dtype=bool)
        key = int(window)
        rank = self._cost_rank.get(key)
        if rank is None:
            span = self.high - self.low
            ratio = self._cost / np.where(span > 1e-12, span, 1e-12)
            rank = ind.rolling_rank(ratio, key)
            self._cost_rank[key] = rank
        return rank <= float(rank_max)

    def ema(self, length: int) -> np.ndarray:
        key = int(length)
        if key not in self._ema:
            self._ema[key] = ind.ema(self.close, key)
        return self._ema[key]

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

    def atr(self, period: int) -> np.ndarray:
        key = int(period)
        if key not in self._atr:
            self._atr[key] = ind.atr(self.high, self.low, self.close, key)
        return self._atr[key]

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
    # What ``t3`` carries. Most families put the T3 level itself there; the
    # two trend-flag families put a -1/0/+1 direction in the same field, and
    # the flip families do not populate it at all. Nothing downstream trades
    # on any of it - it is the live status view - but the view was reading
    # all three as one number. See ``last()``.
    t3_kind: str = "level"

    def last(self) -> dict[str, Any]:
        if self.t3.size < 2:
            return {}
        i = -1
        buy = bool(self.buy[i]) and not bool(self.sell[i])
        sell = bool(self.sell[i]) and not bool(self.buy[i])

        # A family that does not compute one of these passes an all-zero
        # series (the ``zeros`` argument at the flip-family return sites).
        # Reporting that as 0.0 is indistinguishable from a real reading of
        # zero: the live panel showed ADX 0.0 and "t3 falling" for strategies
        # that compute neither, which reads as a bot buying against its own
        # trend filter. None says "this family does not measure it".
        #
        # An all-zero series that a family DID compute is possible in
        # principle and reported the same way; a genuinely flat ADX over the
        # whole warmup says nothing worth distinguishing from "not measured".
        def _reading(series: np.ndarray) -> float | None:
            return float(series[i]) if series.any() else None

        t3_now = _reading(self.t3)
        # Only a level can rise. For the direction families the same
        # comparison would report a -1 -> +1 flip as "t3 rising", which is a
        # different statement in the same words; the flag itself is in ``t3``.
        rising: bool | None = None
        if t3_now is not None and self.t3_kind == "level":
            rising = bool(self.t3[i] > self.t3[i - 1])

        return {
            "t3": t3_now,
            "t3_kind": self.t3_kind if t3_now is not None else None,
            "t3_rising": rising,
            "k": _reading(self.k), "d": _reading(self.d),
            "atr": float(self.atr[i]), "adx": _reading(self.adx),
            "buy": buy,
            "sell": sell,
            "htf": 1 if self.htf_up[i] else (-1 if self.htf_down[i] else 0),
        }


# Names already reported as unknown, so the warning below is emitted once per
# (symbol-less) family name rather than on every bar of every cycle.
_UNKNOWN_FAMILIES: set[str] = set()


def compute(cache: IndicatorCache, p: Params) -> Signals:
    """Route to the configured strategy family.

    An unrecognised name used to fall back to ``_t3_stoch`` silently: the
    symbol went on trading, but a DIFFERENT strategy from the one its config
    named, with no error and no log line. Nothing downstream could tell -
    the panel, the optimizer's holdout and the supervisor's judgement all
    still read the configured name, so a stale row naming a renamed or
    retired family would have been measured, scored and suspended as if it
    were running what it said.

    Refusing to signal is the safe direction: trading nothing costs an
    opportunity, trading something else costs money against a record that
    cannot explain it. The warning is persisted (WARN) and emitted once per
    name, because this can only come from a config that needs fixing.
    """
    if cache.close.size == 0:
        # Same fail-closed as an unknown name. Eight families used to
        # IndexError on an empty series; three did not. Live never hands
        # n=0 in (bars() returns None below 2), but compute() is a leaf
        # other callers reach.
        return _no_signal(cache, p)
    builder = _FAMILIES.get(p.strategy)
    if builder is None:
        if p.strategy not in _UNKNOWN_FAMILIES:
            _UNKNOWN_FAMILIES.add(p.strategy)
            LOG.emit(f"Bilinmeyen strateji ailesi {p.strategy!r} - sinyal "
                     f"uretilmeyecek. Taninanlar: {', '.join(sorted(_FAMILIES))}",
                     "WARN")
        return _no_signal(cache, p)
    return builder(cache, p)


def _no_signal(cache: IndicatorCache, p: Params) -> Signals:
    """Live status series with both entry sides held flat."""
    t3, k, d, atr_series, adx_series = _common(cache, p)
    flat = np.zeros(atr_series.shape, dtype=bool)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series,
                   buy=flat, sell=flat, htf_up=flat, htf_down=flat)


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


def _resolve_conflicts(buy: np.ndarray, sell: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop bars where both sides fired; they cannot both be traded."""
    both = buy & sell
    return buy & ~both, sell & ~both


def _mtf_pullback(cache: IndicatorCache, p: Params) -> Signals:
    """Buy the dip inside a higher-timeframe uptrend (and the mirror).

    The other families all enter on an impulse; none of them waits. This one is
    the continuation trade: the higher timeframe must already be trending (that
    filter is mandatory here, not optional), price must then pull *against* that
    trend by at least ``pull_depth_atr`` ATR and reach the fast EMA, and the
    entry is the first bar that resumes in the trend direction. Buying a
    pullback rather than a breakout puts the stop behind recent structure
    instead of under an extended move, which is where the R:R of a scalp comes
    from. Depth below ``MIN_PULL_DEPTH_ATR`` is noise: the search used to
    offer 0.3 and NAS100's 1.0 ATR stop ate those tickets inside the fill bar.
    """
    close, open_ = cache.close, cache.open
    t3, k, d, atr_series, adx_series = _common(cache, p)
    fast = cache.ema(p.pull_fast)
    regime = _regime(p, adx_series, close.size)

    # The trend leg is required; without it there is no pullback to buy.
    factor = max(2, int(p.htf_factor) if p.htf_factor > 1 else 6)
    up, down = cache.htf(factor, p.t3_length, p.t3_volume_factor)
    htf_up, htf_down = up, down

    depth = atr_series * max(MIN_PULL_DEPTH_ATR, float(p.pull_depth_atr))
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
    if float(p.pull_break_confirm or 0.0) > 0:
        prior_hi = np.roll(cache.high, 1)
        prior_lo = np.roll(cache.low, 1)
        prior_hi[0] = -np.inf
        prior_lo[0] = np.inf
        resume_up = resume_up & (close > prior_hi)
        resume_dn = resume_dn & (close < prior_lo)

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


def _burst(cache: IndicatorCache, p: Params) -> Signals:
    """Continuation off a single range-expansion bar that closed on its extreme.

    A level-based breakout keys off a price the market has already printed -
    a session's opening range, an N-bar channel. None of those can fire on
    the bar that actually matters to a scalper - the one where a burst of
    one-sided activity expands the range well beyond what the last hour has been
    doing and then closes hard against its own extreme, with no prior level
    involved. That bar is the signal here: range above ``brst_range_z`` standard
    deviations of the trailing range distribution, close inside the top (or
    bottom) ``brst_close_pct`` of its own bar, entry on the continuation.

    Because it is anchored to nothing but the current bar it is available at any
    hour, which is the point on M5 - and because a burst is exactly when spreads
    widen, it carries a ``cost_rank_max`` regime gate:
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

    if p.min_body_ratio > 0:
        body = cache.body_ratio()
        buy &= body >= p.min_body_ratio
        sell &= body >= p.min_body_ratio

    warmup = min(close.size, max(window * 4, 260, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    buy = ind.first_of_run(buy)
    sell = ind.first_of_run(sell)
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series, buy=buy, sell=sell,
                   htf_up=htf_up, htf_down=htf_down)


def _channel_break(cache: IndicatorCache, p: Params) -> Signals:
    """Close beyond the highest high (or lowest low) of the prior N bars.

    The one signal shape the book did not have. ``burst`` is range *expansion* -
    this bar's own high-low against its trailing distribution - and says so in
    its own docstring: "a level-based breakout keys off a price the market has
    already printed - a session's opening range, an N-bar channel", which it
    deliberately is not.

    Measured out-of-sample on every captured window before this was written
    (F40): the asymmetry a stop-and-trail system monetises rises smoothly with
    ``chan_lookback`` (median 1.034 at 10 bars, 1.078 at 100) instead of
    spiking at one value. That shape is why the axis exists and why its grid
    runs past burst's ceiling of 40 - the effect lives where the old grid could
    not reach.

    The channel excludes the signal bar. Comparing a close to a high the same
    bar just set would fire on any bar that closed near its own top, which is
    ``burst``'s question, not this one.
    """
    close = cache.close
    size = close.size
    t3, k, d, atr_series, adx_series = _common(cache, p)
    htf_up, htf_down, allow_long, allow_short = _trend_gate(cache, p)
    regime = _regime(p, adx_series, size)

    window = max(2, int(p.chan_lookback))
    _, hi = ind.rolling_min_max(cache.high, window)
    lo, _ = ind.rolling_min_max(cache.low, window)
    # Shift so bar i is compared against the window ending at i-1.
    prev_hi = np.roll(hi, 1)
    prev_lo = np.roll(lo, 1)
    prev_hi[0] = np.inf
    prev_lo[0] = -np.inf

    # A break that only just clears the level is mostly noise around it. The
    # pad is in ATR so it scales with the instrument instead of its price.
    pad = max(0.0, float(p.chan_buffer_atr)) * atr_series
    ok = regime
    if p.atr_pct_min > 0:
        ok = ok & (cache.atr_rank(p.atr_period) >= p.atr_pct_min)

    buy = ok & allow_long & (close > prev_hi + pad)
    sell = ok & allow_short & (close < prev_lo - pad)

    if p.min_body_ratio > 0:
        body = cache.body_ratio()
        buy &= body >= p.min_body_ratio
        sell &= body >= p.min_body_ratio

    warmup = min(size, max(window + 1, p.atr_period * 3))
    buy[:warmup] = False
    sell[:warmup] = False

    # A trend sits outside its own channel for many bars in a row; without this
    # the family would re-signal every one of them.
    buy = ind.first_of_run(buy)
    sell = ind.first_of_run(sell)
    buy, sell = _resolve_conflicts(buy, sell)
    return Signals(t3=t3, k=k, d=d, atr=atr_series, adx=adx_series,
                   buy=buy, sell=sell, htf_up=htf_up, htf_down=htf_down)


_FAMILIES = {
    "mtf_pullback": _mtf_pullback,
    "burst": _burst,
    "channel_break": _channel_break,
}

# Exit / live-entry axes the family function never names. The search and the
# panel still own them: they are enforced in simulate/engine, not in compute().
ENGINE_OPT_FIELDS = frozenset(EXIT_RISK_FIELDS) | {"max_spread_atr", "min_atr_ratio"}


def _p_fields_reachable(fn, seen: set | None = None) -> set[str]:
    """``p.foo`` names this function and same-module callees actually read."""
    seen = seen if seen is not None else set()
    if fn in seen or not callable(fn):
        return set()
    seen.add(fn)
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    except (OSError, TypeError, SyntaxError):
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "p"):
            found.add(node.attr)
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else None
            callee = globals().get(name) if name else None
            if callee is not None and getattr(callee, "__module__", "") == __name__:
                found |= _p_fields_reachable(callee, seen)
    return found


@functools.cache
def opt_fields_read(family: str) -> frozenset[str]:
    """OPT_FIELDS this family's compute path reads. Derived, not a table."""
    fn = _FAMILIES.get(family)
    if fn is None:
        return frozenset()
    return frozenset(_p_fields_reachable(fn) & set(OPT_FIELDS))


def unstamped_gates_to_zero(family: str, stamped: dict[str, Any]) -> dict[str, Any]:
    """Gates a newly-gated flip reads that the apply stamp never named.

    0 disables each. Search that earned a value puts it in ``stamped``.
    dual_t3 leftover ADX on a stoch_flip card must not survive; the same
    ADX sitting on a dual_t3 card is the live dial and must.
    """
    if family not in _GATED_FLIPS or not isinstance(stamped, dict):
        return {}
    read = opt_fields_read(family)
    return {name: 0 for name in _UNSTAMPED_GATES
            if name in read and name not in stamped}


def absent_regime_gates_to_zero(family: str, stamped: dict[str, Any]) -> dict[str, Any]:
    """Zero regime gates a family reads when the search winner did not name them.

    Without this, an apply leaves stale adx_max / min_body_ratio from the
    previous family or an older sweep on the live row - SpotBrent kept
    adx_max=25 while the burst winner only stamped adx_min=0.
    """
    read = opt_fields_read(family)
    return {name: 0 for name in _ABSENT_GATE_ZERO if name in read and name not in stamped}


def searchable_axes(family: str, axes: dict[str, Any]) -> dict[str, Any]:
    """Drop OPT axes the family never reads. Engine axes stay."""
    allow = opt_fields_read(family) | ENGINE_OPT_FIELDS
    return {k: v for k, v in axes.items()
            if k in allow or k not in OPT_FIELDS}


def required_bars(p: Params) -> int:
    """Lookback needed before the indicator stack is trustworthy."""
    # searchable_axes already drops unread OPT axes. This fetch size used to
    # scale by htf_factor even when the family never calls _trend_gate, so a
    # leftover dial (SpotBrent dual_t3, factor 12) asked for 50% more bars
    # than the indicator stack can use (review 24.08 12:15).
    reads_htf = "htf_factor" in opt_fields_read(p.strategy)
    htf = max(1, p.htf_factor if p.htf_mode == "t3" and reads_htf else 1)
    if p.strategy == "mtf_pullback":
        htf = max(htf, 6)            # the trend leg is mandatory for this family
    return int(max(400, p.t3_length * 20 * htf,
                   (p.rsi_length + p.stoch_length + p.smooth_k + p.smooth_d) * 8,
                   p.atr_period * 10, p.adx_period * 10,
                   p.pull_fast * 10,
                   # burst ranks cost against a 240-bar window.
                   p.brst_lookback * 6 + 260,
                   # channel_break needs the full channel before its first read.
                   int(p.chan_lookback) + 2))
