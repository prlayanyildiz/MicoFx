"""Shared robustness gate for income exec landings (Claude 04.09).

Last-segment ``charged_holdout`` alone overfits recent regimes (JPN225 2/6).
A challenger must keep ≥4/6 equal-bar slices ``net_r > 0`` before apply.

Micro-tune erosion (03:36): binary ≥4/6 still allowed 6/6→5/6 drift and
back-loading. Upgrade also requires full-window +5R, non-regression of
slice wins, and ≤15pp rise in last-2-slice share of full net.

``EXEC_PIPELINE_FROZEN`` kills all gated proposes until an operator /
Claude unfreeze (second-tour micro-tunes were eroding robustness).
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from micofx import backtest
from micofx.bar_snapshot import read, snapshot_path
from micofx.models import SymbolConfig
from micofx.mt5client import timeframe_seconds
from micofx.strategy import IndicatorCache, Params, compute
from scripts.session_exec import live_trade_sessions

ROBUST_PARTS = 6
MIN_POSITIVE_SLICES = 4
MIN_FULL_DELTA_R = 5.0
MAX_BACKLOAD_SHARE_RISE = 0.15
# Claude 15:24 — imputed/sparse slices must not count as wins (GER40 dirty head).
MAX_SPREAD_MISSING_RATIO = 0.05
MIN_BARS_PER_DAY_FRAC = 0.50
MIN_SLICE_TRADES = 15
MIN_VALID_SLICES = 4

# Claude 04.09 03:36 — freeze micro-tune lands.
# 03:50 Claude: gate sign-off ≠ unfreeze. Keep frozen until measured
# target + manual run + Claude 6-slice review. Do not flip this casually.
EXEC_PIPELINE_FROZEN = True
_FREEZE_FLAG = Path(__file__).resolve().parents[1] / ".bridge" / "EXEC_PIPELINE_FROZEN"


def pipeline_frozen() -> bool:
    if EXEC_PIPELINE_FROZEN:
        return True
    try:
        return _FREEZE_FLAG.is_file()
    except OSError:
        return False


def slice_quality_ok(
    *,
    spread_missing_ratio: float,
    bars_per_day: float,
    median_bars_per_day: float,
    trades: int,
) -> bool:
    """True when a 6-slice cell is measurable (Claude 15:24).

    Missing raw spread → imputed cost (assumption, not measurement). Sparse
    bars/day → historical thin series. Thin trade count → no statistics.
    """
    if float(spread_missing_ratio) > MAX_SPREAD_MISSING_RATIO + 1e-12:
        return False
    med = float(median_bars_per_day)
    if med > 0 and float(bars_per_day) + 1e-12 < med * MIN_BARS_PER_DAY_FRAC:
        return False
    if int(trades) < int(MIN_SLICE_TRADES):
        return False
    return True


def _median(xs: list[float]) -> float:
    vals = sorted(float(x) for x in xs)
    if not vals:
        return 0.0
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return 0.5 * (vals[mid - 1] + vals[mid])


def valid_slice_wins(nets: list[float], valid: list[bool] | None) -> int:
    if valid is None:
        return slice_wins(nets)
    return sum(
        1 for n, ok in zip(nets, valid, strict=True) if ok and float(n) > 0)


def valid_slice_count(valid: list[bool] | None, n: int) -> int:
    if valid is None:
        return int(n)
    return sum(1 for ok in valid if ok)


def _overlay_row(row: dict[str, Any], field: str | None, value: float | None) -> dict[str, Any]:
    overlay = deepcopy(row)
    for k in ("available", "digits", "description"):
        overlay.pop(k, None)
    if field is not None and value is not None:
        overlay[field] = float(value)
    live_sess = live_trade_sessions(row)
    if not bool(row.get("use_sessions", True)):
        overlay["use_sessions"] = False
    else:
        overlay["sessions"] = live_sess
        overlay["use_sessions"] = True
    return overlay


def charged_slice_report(
    row: dict[str, Any],
    *,
    field: str | None = None,
    value: float | None = None,
    parts: int = ROBUST_PARTS,
) -> dict[str, Any] | None:
    """Equal-width charged slices plus data-quality validity (Claude 15:24)."""
    import numpy as np

    sym = str(row.get("symbol") or "")
    tf = str(row.get("timeframe") or "")
    path = snapshot_path(sym, tf)
    if not path.exists():
        return None
    try:
        snap = read(path)
    except Exception:
        return None
    overlay = _overlay_row(row, field, value)
    try:
        cfg = SymbolConfig.from_dict(overlay)
    except Exception:
        return None
    bars = snap["bars"]
    info = snap["info"]
    n = len(bars)
    parts = max(2, int(parts))
    if n < parts * 40:
        return None
    point = float(info["point"])
    commission = backtest.commission_in_price(
        cfg.commission_per_lot, float(info["tick_value"]), float(info["tick_size"]))
    scale = float(snap["spread_scale"])
    _, spread_price, trigger_pad, min_stop_series = backtest.spread_cost_series(
        bars.spread, point, scale, float(snap["min_stop"]))
    tradable = backtest.session_mask(cfg, bars.time, bool(snap["trade_all_hours"]))
    flatten = backtest.flatten_mask(
        cfg, bars.time, bool(snap["trade_all_hours"]),
        int(snap["day_end_flatten_min"]))
    p = Params.from_config(cfg)
    cost_price = spread_price + float(commission)
    tf_sec = timeframe_seconds(tf)
    cache = IndicatorCache(
        bars.high, bars.low, bars.close, bars.time, tf_sec,
        bars.open, bars.volume, cost_price)
    sig = compute(cache, p)
    width = n // parts
    raw_spread = np.asarray(bars.spread, dtype=np.float64)
    times = np.asarray(bars.time, dtype=np.float64)
    nets: list[float] = []
    trades: list[int] = []
    missing: list[float] = []
    bpd: list[float] = []
    for i in range(parts):
        lo = i * width
        hi = n if i == parts - 1 else lo + width
        res = backtest.simulate(
            cache, sig, bars.open, bars.spread, point, p, tradable,
            lo, hi, commission,
            spread_price=spread_price, min_stop=min_stop_series, flatten=flatten,
            max_open=backtest.max_open_from_cfg(cfg),
            block_reverse=True, trigger_pad=trigger_pad)
        nets.append(float(getattr(res, "net_r", 0.0) or 0.0))
        trades.append(int(getattr(res, "trades", 0) or 0))
        chunk = raw_spread[lo:hi]
        if len(chunk) == 0:
            missing.append(1.0)
            bpd.append(0.0)
            continue
        miss = float(np.mean((~np.isfinite(chunk)) | (chunk <= 0.0)))
        missing.append(miss)
        dt = float(times[hi - 1] - times[lo]) if hi > lo else 0.0
        days = max(dt / 86400.0, 1e-9)
        bpd.append(float(len(chunk)) / days)
    med_bpd = _median(bpd)
    valid = [
        slice_quality_ok(
            spread_missing_ratio=missing[i],
            bars_per_day=bpd[i],
            median_bars_per_day=med_bpd,
            trades=trades[i],
        )
        for i in range(parts)
    ]
    return {
        "nets": nets,
        "trades": trades,
        "spread_missing": missing,
        "bars_per_day": bpd,
        "valid": valid,
        "valid_n": sum(1 for ok in valid if ok),
        "wins_valid": valid_slice_wins(nets, valid),
    }


def charged_slice_nets(
    row: dict[str, Any],
    *,
    field: str | None = None,
    value: float | None = None,
    parts: int = ROBUST_PARTS,
) -> list[float] | None:
    """Equal-width charged ``net_r`` across the full snapshot (oldest→newest)."""
    rep = charged_slice_report(row, field=field, value=value, parts=parts)
    if rep is None:
        return None
    return list(rep["nets"])


def slice_wins(nets: list[float]) -> int:
    return sum(1 for n in nets if n > 0)


def backload_share(nets: list[float]) -> float:
    """Last-two-slice share of |full| using signed full sum (Claude back-load)."""
    if len(nets) < 2:
        return 0.0
    full = sum(nets)
    if abs(full) < 1e-9:
        return 0.0
    return (nets[-2] + nets[-1]) / full


def _mask_nets(nets: list[float], valid: list[bool] | None) -> list[float]:
    if valid is None:
        return list(nets)
    return [float(n) if ok else 0.0 for n, ok in zip(nets, valid, strict=True)]


def upgrade_robust(
    live_nets: list[float] | None,
    chal_nets: list[float] | None,
    *,
    min_positive: int = MIN_POSITIVE_SLICES,
    min_full_delta_r: float = MIN_FULL_DELTA_R,
    max_backload_rise: float = MAX_BACKLOAD_SHARE_RISE,
    live_valid: list[bool] | None = None,
    chal_valid: list[bool] | None = None,
) -> bool:
    """Full-window +ΔR, ≥min_positive wins, no win loss, no back-load spike.

    Also rejects a worse *minimum* slice (Claude 03:50 optional refine:
    5/6→5/6 with a deeper hole is still erosion).

    Optional ``live_valid`` / ``chal_valid`` (Claude 15:24): imputed/sparse
    slices are excluded from wins/min/backload; fewer than ``MIN_VALID_SLICES``
    measurable cells → refuse (insufficient evidence).
    """
    if live_nets is None or chal_nets is None:
        return False
    if len(live_nets) != len(chal_nets):
        return False
    if valid_slice_count(chal_valid, len(chal_nets)) < int(MIN_VALID_SLICES):
        return False
    if valid_slice_count(live_valid, len(live_nets)) < int(MIN_VALID_SLICES):
        return False
    chal_wins = valid_slice_wins(chal_nets, chal_valid)
    live_wins = valid_slice_wins(live_nets, live_valid)
    if chal_wins < int(min_positive):
        return False
    if chal_wins < live_wins:
        return False
    live_m = _mask_nets(live_nets, live_valid)
    chal_m = _mask_nets(chal_nets, chal_valid)
    if sum(chal_m) + 1e-9 < sum(live_m) + float(min_full_delta_r):
        return False
    # Min among measurable slices only.
    live_pos = [n for n, ok in zip(live_nets, live_valid or [True] * len(live_nets), strict=True) if ok]
    chal_pos = [n for n, ok in zip(chal_nets, chal_valid or [True] * len(chal_nets), strict=True) if ok]
    if not live_pos or not chal_pos:
        return False
    if min(chal_pos) + 1e-9 < min(live_pos):
        return False
    rise = backload_share(chal_m) - backload_share(live_m)
    if rise > float(max_backload_rise) + 1e-12:
        return False
    return True


def robust_enough(
    row: dict[str, Any],
    *,
    field: str | None = None,
    value: float | None = None,
    min_positive: int = MIN_POSITIVE_SLICES,
    parts: int = ROBUST_PARTS,
) -> bool:
    """True when challenger (or live row) has ≥``min_positive`` winning slices."""
    rep = charged_slice_report(row, field=field, value=value, parts=parts)
    if rep is None:
        return False
    if int(rep.get("valid_n") or 0) < int(MIN_VALID_SLICES):
        return False
    return int(rep.get("wins_valid") or 0) >= int(min_positive)


def gate_pick(
    row: dict[str, Any],
    pick: dict[str, Any] | None,
    *,
    field: str,
    value_key: str,
) -> dict[str, Any] | None:
    """Drop a charged pick that fails freeze / full / non-regress / back-load."""
    if pipeline_frozen() or pick is None:
        return None
    try:
        val = float(pick[value_key])
    except (KeyError, TypeError, ValueError):
        return None
    live_rep = charged_slice_report(row)
    chal_rep = charged_slice_report(row, field=field, value=val)
    if live_rep is None or chal_rep is None:
        return None
    if not upgrade_robust(
            live_rep["nets"], chal_rep["nets"],
            live_valid=live_rep["valid"], chal_valid=chal_rep["valid"]):
        return None
    return pick


def refuse_msa_widen(
    row: dict[str, Any],
    new_cap: float,
    *,
    min_full_delta_r: float = -1.0,
) -> str | None:
    """Turkish reason if an msa widen fails 6-slice; None if OK / unmeasurable."""
    try:
        old = float(row.get("max_spread_atr") or 0.0)
        nxt = float(new_cap)
    except (TypeError, ValueError):
        return None
    if nxt <= old + 1e-9:
        return None
    live_nets = charged_slice_nets(row)
    chal_nets = charged_slice_nets(row, field="max_spread_atr", value=nxt)
    if live_nets is None or chal_nets is None:
        return None
    if upgrade_robust(
        live_nets, chal_nets, min_full_delta_r=float(min_full_delta_r),
    ):
        return None
    return f"6-slice erozyon ({old:g}->{nxt:g})"
