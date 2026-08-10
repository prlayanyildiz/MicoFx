from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

try:                                       # optional: ~6x faster recursive filters
    from scipy.signal import lfilter as _lfilter
except ImportError:                        # pragma: no cover - scipy is optional
    _lfilter = None


def _recursive(src: np.ndarray, alpha: float, first: float) -> np.ndarray:
    """y[0] = first; y[i] = y[i-1]*(1-alpha) + src[i]*alpha.

    The recursion is a first-order IIR filter, so ``scipy.signal.lfilter``
    computes it in C. The Python fallback below is the original loop and must
    stay bit-comparable: the optimizer's scores depend on these series.
    """
    n = src.size
    if n == 0:
        return np.empty(0, dtype=np.float64)
    beta = 1.0 - alpha
    if _lfilter is not None and n > 1:
        out = np.empty(n, dtype=np.float64)
        out[0] = first
        # zi carries y[0] into the filter so out[1:] continues the recursion.
        out[1:] = _lfilter([alpha], [1.0, -beta], src[1:].astype(np.float64),
                           zi=np.array([beta * first]))[0]
        return out
    values = src.tolist()
    acc = float(first)
    buf = [0.0] * n
    buf[0] = acc
    for i in range(1, n):
        acc = acc * beta + values[i] * alpha
        buf[i] = acc
    return np.asarray(buf, dtype=np.float64)


def ema(src: np.ndarray, length: int) -> np.ndarray:
    """Exponential moving average seeded with the first sample."""
    if src.size == 0:
        return np.empty(0, dtype=np.float64)
    return _recursive(src, 2.0 / (float(length) + 1.0), float(src[0]))


def wilder(src: np.ndarray, length: int, seed: float | None = None) -> np.ndarray:
    """Wilder's smoothing (RMA), the average used by RSI/ATR/ADX."""
    if src.size == 0:
        return np.empty(0, dtype=np.float64)
    # Every other length-taking helper here clamps (sma, ema, atr, rsi, adx);
    # this one did not, so ``1 / length`` below was a ZeroDivisionError on a 0.
    # Its in-module callers all clamp before calling, so nothing reachable hit
    # it - but this is a public helper in a toolkit module, and a future caller
    # passing a period straight from config would find the one function that
    # does not defend itself.
    length = max(1, int(length))
    first = float(seed) if seed is not None else float(src[0])
    return _recursive(src, 1.0 / float(length), first)


def sma(src: np.ndarray, length: int) -> np.ndarray:
    """Simple moving average; the warmup head is filled with expanding means."""
    length = max(1, int(length))
    n = src.size
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    if length == 1:
        return src.astype(np.float64, copy=True)
    head = min(length - 1, n)
    out[:head] = np.cumsum(src[:head]) / np.arange(1, head + 1)
    if n >= length:
        out[length - 1:] = sliding_window_view(src, length).mean(axis=1)
    return out


def rolling_min_max(src: np.ndarray, length: int) -> tuple[np.ndarray, np.ndarray]:
    length = max(1, int(length))
    n = src.size
    lo = np.empty(n, dtype=np.float64)
    hi = np.empty(n, dtype=np.float64)
    if n == 0:
        return lo, hi
    head = min(length - 1, n)
    lo[:head] = np.minimum.accumulate(src[:head])
    hi[:head] = np.maximum.accumulate(src[:head])
    if n >= length:
        win = sliding_window_view(src, length)
        lo[length - 1:] = win.min(axis=1)
        hi[length - 1:] = win.max(axis=1)
    return lo, hi


def rolling_rank(src: np.ndarray, window: int) -> np.ndarray:
    """Fraction of the trailing window each value exceeds, in 0..1.

    Used as a volatility regime gate: a reading near 0 means the market is as
    quiet as it has been all window, which is where scalping edges disappear.
    """
    window = max(2, int(window))
    n = src.size
    out = np.zeros(n, dtype=np.float64)
    if n == 0:
        return out
    if n >= window:
        win = sliding_window_view(src, window)
        out[window - 1:] = (win < win[:, -1:]).sum(axis=1) / (window - 1)
    head = min(window - 1, n)
    for i in range(head):
        if i == 0:
            out[i] = 0.5
        else:
            out[i] = float((src[:i] < src[i]).sum()) / i
    return out


def rolling_std(src: np.ndarray, length: int) -> np.ndarray:
    """Population standard deviation over a trailing window (expanding warmup)."""
    length = max(2, int(length))
    n = src.size
    out = np.zeros(n, dtype=np.float64)
    if n == 0:
        return out
    mean = sma(src, length)
    mean_sq = sma(src * src, length)
    return np.sqrt(np.maximum(mean_sq - mean * mean, 0.0))


def bollinger(close: np.ndarray, length: int, sd: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Classic Bollinger Bands: SMA mid with +/- ``sd`` standard deviations."""
    mid = sma(close, max(2, int(length)))
    dev = rolling_std(close, length) * float(sd)
    return mid, mid + dev, mid - dev


def keltner(high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int,
            atr_mult: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Keltner Channel: EMA mid with +/- ``atr_mult`` ATR."""
    mid = ema(close, max(2, int(length)))
    band = atr(high, low, close, max(2, int(length))) * float(atr_mult)
    return mid, mid + band, mid - band


def linreg_slope(src: np.ndarray, length: int) -> np.ndarray:
    """Slope of a least-squares fit over the trailing ``length`` bars.

    Used as the momentum leg of a squeeze release: the direction a compressed
    range breaks is far better predicted by the slope of the run-up than by the
    breakout bar itself.
    """
    length = max(3, int(length))
    n = src.size
    out = np.zeros(n, dtype=np.float64)
    if n < length:
        return out
    x = np.arange(length, dtype=np.float64)
    x_mean = x.mean()
    denom = float(((x - x_mean) ** 2).sum())
    win = sliding_window_view(src.astype(np.float64), length)
    y_mean = win.mean(axis=1)
    cov = (win * (x - x_mean)).sum(axis=1) - y_mean * (x - x_mean).sum()
    out[length - 1:] = cov / denom
    return out


def close_location_value(open_: np.ndarray, high: np.ndarray, low: np.ndarray,
                         close: np.ndarray) -> np.ndarray:
    """Where a bar closed inside its own range, on -1..+1.

    ``((C-L) - (H-C)) / (H-L)``. This is the standard OHLC proxy for whether a
    bar's volume was accumulated by aggressive buyers or sellers; it is what MT5
    order-flow indicators fall back on for FX, where no true tape exists.
    """
    span = high - low
    safe = np.where(span > 1e-12, span, 1.0)
    clv = ((close - low) - (high - close)) / safe
    return np.where(span > 1e-12, clv, 0.0)


def delta_proxy(open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray,
                volume: np.ndarray) -> np.ndarray:
    """Signed volume proxy: close-location value weighted by (tick) volume.

    Honest about its limits - MT5 gives tick counts, not traded size, and this
    infers aggressor side from candle shape rather than from the tape. It still
    separates bars where volume arrived *into* a direction from bars where the
    same volume produced a rejection wick.
    """
    vol = np.where(volume > 0, volume.astype(np.float64), 1.0)
    return close_location_value(open_, high, low, close) * vol


def rolling_sum(src: np.ndarray, length: int) -> np.ndarray:
    """Trailing sum with an expanding warmup head."""
    length = max(1, int(length))
    n = src.size
    out = np.zeros(n, dtype=np.float64)
    if n == 0:
        return out
    cum = np.cumsum(src.astype(np.float64))
    out[:min(length, n)] = cum[:min(length, n)]
    if n > length:
        out[length:] = cum[length:] - cum[:-length]
    return out


def zscore(src: np.ndarray, window: int) -> np.ndarray:
    """Standard score of each value against its own trailing window."""
    window = max(3, int(window))
    mean = sma(src, window)
    sd = rolling_std(src, window)
    return np.where(sd > 1e-12, (src - mean) / np.where(sd > 1e-12, sd, 1.0), 0.0)


def macd(close: np.ndarray, fast: int, slow: int, signal: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Classic MACD: fast/slow EMA spread, its own EMA as the signal line.

    Genuinely different information from the T3 families already in this file:
    T3 reads a single smoothed price line's own direction, MACD reads the
    *spread* between two EMAs of different speed - a momentum divergence
    read, not a price-smoothing read. Two lines converging/diverging can flip
    ahead of a slow line's own direction change.
    """
    fast_ema = ema(close, max(1, int(fast)))
    slow_ema = ema(close, max(1, int(slow)))
    line = fast_ema - slow_ema
    sig = ema(line, max(1, int(signal)))
    return line, sig, line - sig


def wavetrend(high: np.ndarray, low: np.ndarray, close: np.ndarray,
             channel_len: int, avg_len: int) -> tuple[np.ndarray, np.ndarray]:
    """WaveTrend oscillator (LazyBear's formula): wt1 (fast) and wt2 (its SMA-4 signal).

    A third read on the same OHLC data, mathematically distinct from both T3
    (single smoothed price line) and MACD (spread of two same-input EMAs):
    WaveTrend normalises price against its own *mean absolute deviation* from
    a smoothed typical price, so its scale is bounded and comparable across
    symbols/volatility regimes rather than a raw price-unit spread. wt1
    crossing wt2 is the flip; nothing here reads the classic +-60/100
    overbought/oversold bands, that is a separate, optional read a family can
    still add on top.
    """
    channel_len = max(1, int(channel_len))
    avg_len = max(1, int(avg_len))
    typical = (high + low + close) / 3.0
    esa = ema(typical, channel_len)
    d = ema(np.abs(typical - esa), channel_len)
    ci = (typical - esa) / np.where(d > 1e-12, 0.015 * d, 1.0)
    wt1 = ema(ci, avg_len)
    wt2 = sma(wt1, 4)
    return wt1, wt2


def stochastic_slow(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                    k_period: int, k_smooth: int, d_smooth: int) -> tuple[np.ndarray, np.ndarray]:
    """Classic slow Stochastic: %K = close's position in its own H/L range,
    smoothed twice (raw %K -> slow %K -> slow %D).

    Not the same read as ``stoch_rsi`` (Stochastic applied to RSI, already
    used by ``t3_stoch``) - this measures where price sits inside its own
    recent high/low range directly, RSI is never computed. A fourth
    mathematically distinct basis alongside T3 (price smoothing), MACD (EMA
    spread) and WaveTrend (deviation-normalised oscillator).
    """
    period = max(1, int(k_period))
    hi = rolling_min_max(high, period)[1]
    lo = rolling_min_max(low, period)[0]
    span = hi - lo
    raw_k = np.where(span > 1e-12, (close - lo) / np.where(span > 1e-12, span, 1.0) * 100.0, 50.0)
    slow_k = sma(raw_k, max(1, int(k_smooth)))
    slow_d = sma(slow_k, max(1, int(d_smooth)))
    return slow_k, slow_d


def t3_source(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    return (high + low + 2.0 * close) / 4.0


def tillson_t3(src: np.ndarray, length: int, volume_factor: float) -> np.ndarray:
    """Tillson T3: six cascaded EMAs recombined with the volume-factor weights."""
    length = max(1, int(length))
    vf = float(volume_factor)
    e1 = ema(src, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    e4 = ema(e3, length)
    e5 = ema(e4, length)
    e6 = ema(e5, length)
    vf2 = vf * vf
    vf3 = vf2 * vf
    c1 = -vf3
    c2 = 3.0 * vf2 + 3.0 * vf3
    c3 = -6.0 * vf2 - 3.0 * vf - 3.0 * vf3
    c4 = 1.0 + 3.0 * vf + vf3 + 3.0 * vf2
    return c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3


def htf_t3_trend(times: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray,
                 bucket_seconds: int, length: int, volume_factor: float) -> tuple[np.ndarray, np.ndarray]:
    """T3 direction of a higher timeframe, mapped back onto the base bars.

    Bars are bucketed by wall-clock time so the result does not depend on where
    the array happens to start, and each base bar only ever sees the *previous*
    completed higher-timeframe bar. Both properties are required for the live
    engine and the backtester to agree.
    """
    n = close.size
    empty = np.zeros(n, dtype=bool)
    if n == 0 or bucket_seconds <= 0:
        return empty, empty

    buckets = times.astype(np.int64) // int(bucket_seconds)
    uniq, first = np.unique(buckets, return_index=True)
    if uniq.size < 4:
        return empty, empty

    last = np.append(first[1:], n) - 1
    hi = np.maximum.reduceat(high, first)
    lo = np.minimum.reduceat(low, first)
    cl = close[last]

    t3 = tillson_t3(t3_source(hi, lo, cl), length, volume_factor)
    prev = np.roll(t3, 1)
    prev[0] = t3[0]
    rising_b = t3 > prev
    falling_b = t3 < prev

    pos = np.searchsorted(uniq, buckets) - 1  # only completed buckets are visible
    valid = pos >= 0
    rising, falling = empty.copy(), empty.copy()
    rising[valid] = rising_b[pos[valid]]
    falling[valid] = falling_b[pos[valid]]
    return rising, falling


def session_index(times: np.ndarray, session_start_min: int) -> np.ndarray:
    """Group bars into trading sessions that begin at ``session_start_min``.

    Bars before the day's session start belong to the previous session, so an
    index that opens at 16:30 keeps its whole evening in one bucket.
    """
    shifted = times.astype(np.int64) - int(session_start_min) * 60
    return shifted // 86400


def session_vwap(times: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray,
                 volume: np.ndarray, session_start_min: int) -> tuple[np.ndarray, np.ndarray]:
    """Session-anchored VWAP and its volume-weighted standard deviation.

    Institutional flow is benchmarked against VWAP, which is why stretched
    distance from it mean-reverts far more reliably than VWAP crossovers trend.
    """
    n = close.size
    if n == 0:
        return np.zeros(0), np.zeros(0)

    sess = session_index(times, session_start_min)
    typical = (high + low + close) / 3.0
    vol = np.where(volume > 0, volume, 1.0)

    # Cumulative sums restarted at every session boundary.
    starts = np.flatnonzero(np.diff(sess, prepend=sess[0] - 1) != 0)
    cum_v = np.cumsum(vol)
    cum_pv = np.cumsum(typical * vol)
    cum_pv2 = np.cumsum(typical * typical * vol)

    base = np.zeros(n, dtype=np.float64)
    base_pv = np.zeros(n, dtype=np.float64)
    base_pv2 = np.zeros(n, dtype=np.float64)
    for s in starts:
        if s > 0:
            base[s:] = cum_v[s - 1]
            base_pv[s:] = cum_pv[s - 1]
            base_pv2[s:] = cum_pv2[s - 1]

    v = np.maximum(cum_v - base, 1e-9)
    pv = cum_pv - base_pv
    pv2 = cum_pv2 - base_pv2
    vwap = pv / v
    variance = np.maximum(pv2 / v - vwap * vwap, 0.0)
    return vwap, np.sqrt(variance)


def opening_range(times: np.ndarray, high: np.ndarray, low: np.ndarray,
                  session_start_min: int, minutes: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """High/low of each session's first ``minutes``, broadcast to every bar.

    The third return value marks bars that come *after* the range is complete,
    which are the only ones allowed to trade the breakout.
    """
    n = high.size
    empty = np.zeros(n, dtype=np.float64)
    if n == 0:
        return empty, empty, np.zeros(n, dtype=bool)

    sess = session_index(times, session_start_min)
    minute_of_day = (times.astype(np.int64) - int(session_start_min) * 60) % 86400 // 60
    in_range = minute_of_day < int(minutes)
    after = ~in_range

    uniq, inverse = np.unique(sess, return_inverse=True)
    hi = np.full(uniq.size, -np.inf)
    lo = np.full(uniq.size, np.inf)
    count = np.zeros(uniq.size, dtype=np.int64)
    np.maximum.at(hi, inverse[in_range], high[in_range])
    np.minimum.at(lo, inverse[in_range], low[in_range])
    np.add.at(count, inverse[in_range], 1)

    usable = count >= 1
    hi = np.where(usable, hi, np.nan)
    lo = np.where(usable, lo, np.nan)
    return hi[inverse], lo[inverse], after & usable[inverse]


def donchian(high: np.ndarray, low: np.ndarray, length: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Highest high / lowest low of the ``length`` bars *before* each bar.

    The current bar is excluded so a close above the channel is a genuine break
    of prior structure rather than a comparison against itself. The third value
    marks bars with a full lookback behind them.
    """
    length = max(2, int(length))
    n = high.size
    if n == 0:
        return np.zeros(0), np.zeros(0), np.zeros(0, dtype=bool)
    lo_l, _ = rolling_min_max(low, length)
    _, hi_h = rolling_min_max(high, length)
    prior_hi = np.roll(hi_h, 1)
    prior_lo = np.roll(lo_l, 1)
    prior_hi[0], prior_lo[0] = hi_h[0], lo_l[0]
    valid = np.zeros(n, dtype=bool)
    valid[min(n, length):] = True
    return prior_hi, prior_lo, valid


def first_of_run(flags: np.ndarray) -> np.ndarray:
    """Keep only the bar that starts each True run.

    A trend keeps price outside a breakout channel for many bars; without this
    the same move would be re-signalled on every one of them.
    """
    if flags.size == 0:
        return flags
    prev = np.roll(flags, 1)
    prev[0] = False
    return flags & ~prev


def first_per_group(flags: np.ndarray, group: np.ndarray) -> np.ndarray:
    """Keep only the first True in each group; later repeats are dropped."""
    out = np.zeros_like(flags)
    idx = np.flatnonzero(flags)
    if idx.size == 0:
        return out
    keep = np.empty(idx.size, dtype=bool)
    keep[0] = True
    keep[1:] = group[idx[1:]] != group[idx[:-1]]
    out[idx[keep]] = True
    return out


def any_before_in_group(flags: np.ndarray, group: np.ndarray) -> np.ndarray:
    """True at bar i if `flags` fired at any earlier bar in the same group (session).

    Used for retest logic: "already broke out earlier this session". Vectorized
    cumulative count with a reset at each group boundary so a prior session's
    breakout never leaks into the next one.
    """
    if flags.size == 0:
        return flags.astype(bool)
    flags_i = flags.astype(np.int64)
    csum = np.cumsum(flags_i)
    change = np.empty(group.shape, dtype=bool)
    change[0] = True
    change[1:] = group[1:] != group[:-1]
    starts = np.flatnonzero(change)
    baseline_at_start = csum[starts] - flags_i[starts]  # count strictly before each group started
    counts = np.diff(np.append(starts, group.size))
    baseline = np.repeat(baseline_at_start, counts)
    before_count = csum - flags_i - baseline  # count within this group, strictly before this bar
    return before_count > 0


def rsi(close: np.ndarray, length: int) -> np.ndarray:
    length = max(2, int(length))
    n = close.size
    if n < 2:
        return np.full(n, 50.0)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0.0, delta, 0.0)
    loss = np.where(delta < 0.0, -delta, 0.0)
    seed = max(1, min(length, n))
    avg_gain = wilder(gain, length, seed=float(gain[:seed].mean()))
    avg_loss = wilder(loss, length, seed=float(loss[:seed].mean()))
    rs = np.divide(avg_gain, avg_loss, out=np.full(n, np.inf), where=avg_loss > 0.0)
    out = 100.0 - (100.0 / (1.0 + rs))
    out[avg_loss <= 0.0] = np.where(avg_gain[avg_loss <= 0.0] > 0.0, 100.0, 50.0)
    return out


def stoch_rsi(close: np.ndarray, rsi_length: int, stoch_length: int,
              smooth_k: int, smooth_d: int) -> tuple[np.ndarray, np.ndarray]:
    """Stochastic RSI %K / %D on a 0..100 scale."""
    r = rsi(close, rsi_length)
    lo, hi = rolling_min_max(r, stoch_length)
    span = hi - lo
    raw = np.where(span > 1e-12, (r - lo) / np.where(span > 1e-12, span, 1.0) * 100.0, 50.0)
    k = sma(raw, smooth_k)
    d = sma(k, smooth_d)
    return k, d


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    if close.size == 0:
        # ``prev[0] = close[0]`` below is an IndexError on an empty series, and
        # atr() already carries an ``if tr.size`` guard for exactly this case -
        # it just never got the chance to use it, because the crash happens one
        # call earlier. Completing the guard here rather than in atr() keeps
        # every caller (atr, adx) covered by one check, and matches the empty
        # handling wilder()/sma() already have.
        return np.empty(0, dtype=np.float64)
    prev = np.roll(close, 1)
    prev[0] = close[0]
    return np.maximum(high - low, np.maximum(np.abs(high - prev), np.abs(low - prev)))


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int) -> np.ndarray:
    length = max(1, int(length))
    tr = true_range(high, low, close)
    seed = max(1, min(length, tr.size))
    return wilder(tr, length, seed=float(tr[:seed].mean()) if tr.size else 0.0)


def supertrend(high: np.ndarray, low: np.ndarray, close: np.ndarray,
               period: int, multiplier: float) -> np.ndarray:
    """SuperTrend direction: +1 while the band sits below price, -1 above it.

    The construction is an ATR envelope around the bar midpoint ``(H+L)/2``:
    ``hl2 +/- multiplier * ATR(period)``. Each band is then allowed to ratchet
    only *toward* price - the upper band may fall but never rise while the trend
    is down, and the mirror for the lower band - which is what turns a pair of
    bands into a single trailing line. Direction flips when a **close** breaks
    the currently active band, so the flip bar is a closed-bar fact and carries
    no intrabar lookahead.

    This is deliberately the only confirmation layer offered to ``dual_t3``: it
    is built from nothing but ATR, so it stays inside the same vocabulary as the
    T3 lines and the ATR exits rather than importing a second indicator family.
    """
    n = close.size
    if n == 0:
        return np.zeros(0, dtype=np.int8)
    atr_s = atr(high, low, close, max(1, int(period)))
    mult = max(0.1, float(multiplier))
    hl2 = (high + low) * 0.5
    up_raw = hl2 + mult * atr_s
    dn_raw = hl2 - mult * atr_s
    upper = up_raw.tolist()
    lower = dn_raw.tolist()
    c = close.tolist()
    direction = np.ones(n, dtype=np.int8)
    dirs = direction.tolist()
    for i in range(1, n):
        if not (up_raw[i] < upper[i - 1] or c[i - 1] > upper[i - 1]):
            upper[i] = upper[i - 1]
        if not (dn_raw[i] > lower[i - 1] or c[i - 1] < lower[i - 1]):
            lower[i] = lower[i - 1]
        if c[i] > upper[i - 1]:
            dirs[i] = 1
        elif c[i] < lower[i - 1]:
            dirs[i] = -1
        else:
            dirs[i] = dirs[i - 1]
    return np.asarray(dirs, dtype=np.int8)


def parabolic_sar(high: np.ndarray, low: np.ndarray,
                  af_step: float, af_max: float) -> np.ndarray:
    """Wilder's Parabolic SAR direction (+1/-1), the dot flip as a signed line.

    Neither a smoothed price (T3), an MA spread (MACD), a deviation-normalised
    oscillator (WaveTrend) nor a range-position oscillator (Stochastic) - the
    SAR walks toward price at an *accelerating* rate that resets to the slow
    step every time a new extreme is made, and flips side the instant price
    crosses it. Same trailing-band shape as SuperTrend, different construction
    entirely: SuperTrend's band width is ATR, SAR's is its own acceleration
    factor times the distance to the last extreme.
    """
    n = high.size
    if n == 0:
        return np.zeros(0, dtype=np.int8)
    step = max(0.001, float(af_step))
    cap = max(step, float(af_max))
    hi = high.tolist()
    lo = low.tolist()
    direction = [1] * n
    trend = 1
    sar = lo[0]
    ep = hi[0]
    af = step
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if trend == 1:
            sar = min(sar, lo[i - 1], lo[i - 2] if i >= 2 else lo[i - 1])
            if lo[i] < sar:
                trend = -1
                sar = ep
                ep = lo[i]
                af = step
            elif hi[i] > ep:
                ep = hi[i]
                af = min(af + step, cap)
        else:
            sar = max(sar, hi[i - 1], hi[i - 2] if i >= 2 else hi[i - 1])
            if hi[i] > sar:
                trend = 1
                sar = ep
                ep = hi[i]
                af = step
            elif lo[i] < ep:
                ep = lo[i]
                af = min(af + step, cap)
        direction[i] = trend
    return np.asarray(direction, dtype=np.int8)


def trix(close: np.ndarray, length: int) -> np.ndarray:
    """TRIX: rate of change of a triple-smoothed EMA, as a percentage.

    Three cascaded EMAs of the same length filter out far more noise than any
    single-pass smoothing (T3's cascade included, which recombines its six
    EMAs with weights rather than just re-smoothing the output three times) -
    the tradeoff is lag, which is the point: this is meant to be the *slow,
    clean* read sitting next to the fast flip families, not another fast one.
    """
    if close.size == 0:
        # Same shape as true_range's guard: ema() already returns empty for an
        # empty input, so the cascade below is fine - it is the ``prev[0]``
        # seeding that indexes into nothing.
        return np.empty(0, dtype=np.float64)
    e1 = ema(close, max(1, int(length)))
    e2 = ema(e1, max(1, int(length)))
    e3 = ema(e2, max(1, int(length)))
    prev = np.roll(e3, 1)
    prev[0] = e3[0]
    return np.where(prev != 0, (e3 - prev) / np.where(prev != 0, np.abs(prev), 1.0) * 100.0, 0.0)


def aroon(high: np.ndarray, low: np.ndarray, length: int) -> np.ndarray:
    """Aroon oscillator: 100 * (bars-since-highest-high - bars-since-lowest-low) / length.

    Nothing else in this file reads *time since the last extreme* - every
    other family measures a price level, a spread, or a deviation. Aroon
    measures how recently a high/low was set, so it can read "this trend is
    aging" (both sides drifting toward zero) or "brand new extreme just
    printed" (one side pinned at +-100) in a way none of the price-based
    reads can.
    """
    n = high.size
    length = max(1, int(length))
    osc = np.zeros(n, dtype=np.float64)
    win = length + 1
    if n < win:
        return osc
    h_win = sliding_window_view(high, win)
    l_win = sliding_window_view(low, win)
    up_idx = np.argmax(h_win, axis=1)     # 0 = extreme at window start (oldest), length = current bar
    dn_idx = np.argmin(l_win, axis=1)
    aroon_up = 100.0 * up_idx / length
    aroon_dn = 100.0 * dn_idx / length
    osc[win - 1:] = aroon_up - aroon_dn
    return osc


def adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int) -> np.ndarray:
    """Wilder's ADX; returns only the ADX line (trend-strength filter)."""
    length = max(2, int(length))
    n = close.size
    if n < length + 2:
        return np.zeros(n, dtype=np.float64)
    up = np.diff(high, prepend=high[0])
    dn = -np.diff(low, prepend=low[0])
    plus_dm = np.where((up > dn) & (up > 0.0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0.0), dn, 0.0)
    tr = true_range(high, low, close)
    atr_s = wilder(tr, length, seed=float(tr[:length].mean()))
    plus_s = wilder(plus_dm, length, seed=float(plus_dm[:length].mean()))
    minus_s = wilder(minus_dm, length, seed=float(minus_dm[:length].mean()))
    safe = np.where(atr_s > 1e-12, atr_s, 1.0)
    plus_di = 100.0 * plus_s / safe
    minus_di = 100.0 * minus_s / safe
    total = plus_di + minus_di
    dx = np.where(total > 1e-12, 100.0 * np.abs(plus_di - minus_di) / np.where(total > 1e-12, total, 1.0), 0.0)
    return wilder(dx, length, seed=float(dx[:length].mean()))


def _rolling_edge(values: np.ndarray, lookback: int, pad: float, reduce) -> np.ndarray:
    """Vectorized `reduce` (min/max) over the trailing `lookback` bars, excluding
    the current bar (window for i is values[max(0, i-lookback):i]).

    Causal by construction, so it is safe to use in both the live structure
    trail and the backtest replay without leaking future information.
    """
    lookback = max(1, int(lookback))
    n = values.size
    if n == 0:
        return values.copy()
    padded = np.concatenate([np.full(lookback, pad, dtype=float), values.astype(float)])
    windows = np.lib.stride_tricks.sliding_window_view(padded, lookback)  # shape (n+1, lookback)
    out = reduce(windows, axis=1)
    out[0] = values[0]  # no history yet; fall back to the bar itself
    return out[:n]


def swing_lows(low: np.ndarray, lookback: int = 5) -> np.ndarray:
    """Rolling minimum of the last `lookback` bars, excluding the current bar."""
    return _rolling_edge(low, lookback, np.inf, np.min)


def swing_highs(high: np.ndarray, lookback: int = 5) -> np.ndarray:
    """Rolling maximum of the last `lookback` bars, excluding the current bar."""
    return _rolling_edge(high, lookback, -np.inf, np.max)
