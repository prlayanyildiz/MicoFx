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
    """Exponential moving average seeded with the first sample.

    ``length`` is clamped the same way every sibling here clamps it - see
    wilder(), which was fixed for exactly this and whose comment already
    claimed this function defended itself. It did not, and the smoothing
    factor ``2 / (length + 1)`` fails in two different ways below zero:

        length == -1  ->  2.0 / 0.0, a ZeroDivisionError
        length <= -2  ->  a NEGATIVE alpha, which is the worse case - no
                          error at all, just a recursion that oscillates and
                          diverges. ema(x, -2) over a gentle 100..110 ramp
                          returns -7.3e22, and that flows straight into
                          signal generation as an ordinary number.

    Zero was wrong too, if quietly: alpha becomes 2.0, outside the (0, 1]
    range the recursion assumes.

    Reachable, not theoretical. ``pull_fast`` feeds this directly and both
    POST /api/symbols/{symbol} and POST /api/opt/params accept a negative
    value with HTTP 200 - the bounds checks there only cover the exit axes.
    """
    if src.size == 0:
        return np.empty(0, dtype=np.float64)
    length = max(1, int(length))
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
