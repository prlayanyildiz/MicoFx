"""Every public indicator, against degenerate inputs.

The indicator module is the numeric floor under every strategy, and its inputs
come from broker data - a short warmup, a flat session, a gap that produces a
zero span. This walks all 37 public functions through empty / one-element /
shorter-than-period / flat / zero / NaN / inf series and period values of
0, 1 and longer-than-the-series, asserting none of them raises.

Two gaps this found, both unreachable from live paths (the engine requires 60
bars before building an IndicatorCache, the optimizer 600, and risk.py skips a
symbol whose series is shorter than its ATR period) but both inconsistent with
the module's own conventions:

  * true_range() raised IndexError on an empty series, even though atr() has
    an ``if tr.size`` guard written for exactly that case - the crash happened
    one call earlier, so the guard could never fire.
  * wilder() was the only length-taking helper here without a clamp, so a 0
    period was a ZeroDivisionError. Its in-module callers all clamp first.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import indicators as ind

N = 60

PUBLIC = sorted(
    name for name in dir(ind)
    if not name.startswith("_")
    and callable(getattr(ind, name))
    and getattr(getattr(ind, name), "__module__", "") == ind.__name__
)


def _series(kind: str, n: int) -> np.ndarray:
    if n == 0:
        return np.array([], dtype=float)
    base = np.linspace(100.0, 110.0, n)
    if kind == "flat":
        return np.full(n, 100.0)          # zero variance: division-by-span risk
    if kind == "zeros":
        return np.zeros(n)
    if kind == "nan":
        base = base.copy()
        base[n // 2] = np.nan
    elif kind == "inf":
        base = base.copy()
        base[n // 2] = np.inf
    return base


def _args(fn, kind: str, n: int, period: int) -> list:
    """Build a plausible call for any of these signatures, by parameter name."""
    out = []
    for name, p in inspect.signature(fn).parameters.items():
        low = name.lower()
        if low in ("src", "close", "open_"):
            out.append(_series(kind, n))
        elif low == "high":
            out.append(_series(kind, n) + 0.5)
        elif low == "low":
            out.append(_series(kind, n) - 0.5)
        elif low == "volume":
            out.append(np.ones(n))
        elif low == "times":
            out.append(np.arange(n, dtype=np.int64) * 300)
        elif low == "flags":
            out.append(np.zeros(n, dtype=bool))
        elif low == "group":
            out.append(np.zeros(n, dtype=np.int64))
        elif p.default is not inspect.Parameter.empty:
            out.append(p.default)
        elif low == "bucket_seconds":
            out.append(3600)
        elif low in ("session_start_min", "seed"):
            out.append(0)
        elif low in ("sd", "atr_mult", "multiplier", "volume_factor", "af_step", "af_max"):
            out.append(2.0)
        else:
            out.append(period)            # every remaining name is a period
    return out


CASES = [
    ("bos-dizi", "normal", 0, 14),
    ("tek-eleman", "normal", 1, 14),
    ("periyottan-kisa", "normal", 5, 14),
    ("sabit-seri", "flat", N, 14),
    ("sifir-seri", "zeros", N, 14),
    ("nan-icerir", "nan", N, 14),
    ("inf-icerir", "inf", N, 14),
    ("periyot-0", "normal", N, 0),
    ("periyot-1", "normal", N, 1),
    ("periyot-seriden-uzun", "normal", N, N * 3),
]


def test_the_public_surface_is_what_this_file_thinks_it_is():
    """Guard the sweep: a renamed or new indicator must not silently escape.

    Twenty-eight since the six unsearched families were removed and took nine
    indicators with them - bollinger, keltner, linreg_slope, donchian,
    opening_range, session_vwap, session_index and the two group helpers had no
    caller left once orb, vwap_rev, donchian, squeeze_brk, t3_ribbon and
    liq_sweep were gone. rolling_rank stayed: cost_rank and the ATR rank still
    use it.
    """
    assert len(PUBLIC) >= 28, PUBLIC
    for expected in ("atr", "rsi", "adx", "wilder", "true_range", "supertrend"):
        assert expected in PUBLIC


@pytest.mark.parametrize("case,kind,n,period", CASES, ids=[c[0] for c in CASES])
def test_no_indicator_raises_on_degenerate_input(case, kind, n, period):
    broken = []
    for name in PUBLIC:
        fn = getattr(ind, name)
        try:
            args = _args(fn, kind, n, period)
        except (TypeError, ValueError):
            continue                       # signature this harness cannot build
        try:
            with np.errstate(all="ignore"):
                fn(*args)
        except Exception as exc:           # noqa: BLE001 - reporting every kind
            broken.append(f"{name}: {type(exc).__name__}: {exc}")
    assert not broken, f"[{case}] " + " | ".join(broken)


def test_true_range_returns_empty_rather_than_raising():
    """The specific gap: atr()'s own empty guard could never be reached."""
    empty = np.array([], dtype=float)
    assert ind.true_range(empty, empty, empty).size == 0
    assert ind.atr(empty, empty, empty, 14).size == 0
    assert ind.adx(empty, empty, empty, 14).size == 0


def test_wilder_clamps_its_period_like_every_sibling():
    src = np.linspace(1.0, 10.0, 20)
    assert np.allclose(ind.wilder(src, 0), ind.wilder(src, 1))
    assert np.all(np.isfinite(ind.wilder(src, 0)))


def test_a_clean_series_never_produces_inf():
    """NaN/inf in equals NaN/inf out is fine; manufacturing one is not."""
    n = N
    high, low, close = _series("normal", n) + 0.5, _series("normal", n) - 0.5, _series("normal", n)
    for name in PUBLIC:
        fn = getattr(ind, name)
        try:
            args = _args(fn, "normal", n, 14)
        except (TypeError, ValueError):
            continue
        with np.errstate(all="ignore"):
            res = fn(*args)
        for i, arr in enumerate(res if isinstance(res, tuple) else (res,)):
            arr = np.asarray(arr, dtype=float)
            if arr.size:
                assert not np.isinf(arr).any(), f"{name} cikti[{i}] inf uretti"
