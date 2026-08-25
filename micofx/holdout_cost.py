"""File-only holdout cost/R share. Does not import engine or mt5client.

``_holdout_costed`` stays the apply path and still talks to the bot's own
client. This module is the night measurement: same slice arithmetic, pinned
snapshot inputs, per-trade cost/R share against the live 18% gate.

Do not drop expensive trades and rescore. Live would have refused the fill,
so the rest of the sequence would have been different. Report the share.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from . import backtest
from .logbus import LOG
from .models import SymbolConfig
from .strategy import IndicatorCache, Params, compute

_TF_SECONDS = {"M5": 300, "M15": 900, "M30": 1800}


def _tf_seconds(name: str) -> int:
    key = str(name).upper()
    if key not in _TF_SECONDS:
        raise ValueError(f"unknown timeframe {name!r} - no silent M5 fallback")
    return _TF_SECONDS[key]


def charged_holdout(*, bars, cfg: SymbolConfig, point: float, tick_value: float,
                    tick_size: float, spread_scale: float, min_stop: float | None,
                    segments: int, trade_all_hours: bool, day_end_flatten_min: int,
                    tf_seconds: int):
    """One charged holdout slice. Inputs already resolved — no client, no store.

    Apply gathers from the live terminal; replay gathers from the snapshot.
    The arithmetic lives here once so the two cannot drift (review 24.08 09:20).
    """
    n = len(bars)
    segs = int(segments)
    if n < 800 or n < segs * 150:
        raise ValueError(f"window too short for holdout edges: n={n} segments={segs}")
    edges = [int(round(n * i / segs)) for i in range(segs + 1)]
    lo, hi = edges[-2], edges[-1]
    commission = backtest.commission_in_price(
        cfg.commission_per_lot, float(tick_value or 0), float(tick_size or 0))
    scale = float(spread_scale)
    _, spread_price, trigger_pad, min_stop_series = backtest.spread_cost_series(
        bars.spread, point, scale, min_stop)
    tradable = backtest.session_mask(cfg, bars.time, bool(trade_all_hours))
    flatten = backtest.flatten_mask(
        cfg, bars.time, bool(trade_all_hours), int(day_end_flatten_min))
    p = Params.from_config(cfg)
    cost_price = spread_price + float(commission)
    cache = IndicatorCache(bars.high, bars.low, bars.close, bars.time, tf_seconds,
                           bars.open, bars.volume, cost_price)
    sig = compute(cache, p)
    res = backtest.simulate(
        cache, sig, bars.open, bars.spread, point, p, tradable,
        lo, hi, commission,
        spread_price=spread_price, min_stop=min_stop_series, flatten=flatten,
        max_open=backtest.max_open_from_cfg(cfg),
        block_reverse=True, trigger_pad=trigger_pad)
    return res, lo, hi


def cost_share(cost_rs: list[float] | np.ndarray, trade_rs: list[float] | np.ndarray,
               threshold_pct: float) -> dict[str, Any]:
    """n / median / p90 / share above the live cost gate. No net R."""
    costs = np.asarray(cost_rs, dtype=float)
    rs = np.asarray(trade_rs, dtype=float)
    if costs.size != rs.size:
        raise ValueError("trade_cost_rs and trade_rs must be the same length")
    n = int(costs.size)
    if n == 0:
        return {
            "n": 0, "median": None, "p90": None,
            "threshold_pct": float(threshold_pct),
            "n_above": 0, "share_above": None,
            "wins_above": 0, "losses_above": 0,
        }
    thr = float(threshold_pct) / 100.0
    above = costs > thr
    n_above = int(np.count_nonzero(above))
    return {
        "n": n,
        "median": float(np.median(costs)),
        "p90": float(np.percentile(costs, 90)),
        "threshold_pct": float(threshold_pct),
        "n_above": n_above,
        "share_above": n_above / n,
        "wins_above": int(np.count_nonzero(above & (rs > 0))),
        "losses_above": int(np.count_nonzero(above & (rs <= 0))),
    }


def replay(snap: dict[str, Any]) -> dict[str, Any]:
    """Charged holdout share from a snapshot. No client, no store, no live histogram."""
    if not snap.get("charge_costs"):
        raise ValueError("snapshot charge_costs is off - refusing a cost-free replay")
    info = snap["info"]
    point = float(info["point"])
    if not point > 0:
        raise ValueError("snapshot point must be positive")
    bars = snap["bars"]
    segments = int(snap["segments"])
    n = len(bars)
    if n < 800 or n < segments * 150:
        raise ValueError(f"snapshot window too short for holdout edges: n={n} segments={segments}")
    cfg = SymbolConfig.from_dict(dict(snap["config"]))
    overlay = cfg.to_dict()
    overlay["timeframe"] = snap["timeframe"]
    overlay["symbol"] = snap["symbol"]
    tmp = SymbolConfig.from_dict(overlay)
    res, lo, hi = charged_holdout(
        bars=bars, cfg=tmp, point=point,
        tick_value=float(info.get("tick_value") or 0),
        tick_size=float(info.get("tick_size") or 0),
        spread_scale=float(snap["spread_scale"]),
        min_stop=float(snap["min_stop"]),
        segments=segments,
        trade_all_hours=bool(snap["trade_all_hours"]),
        day_end_flatten_min=int(snap["day_end_flatten_min"]),
        tf_seconds=_tf_seconds(snap["timeframe"]))
    report = cost_share(res.trade_cost_rs, res.trade_rs, float(snap["max_cost_pct_of_risk"]))
    report["symbol"] = snap["symbol"]
    report["timeframe"] = snap["timeframe"]
    report["spread_scale"] = float(snap["spread_scale"])
    report["lo"] = lo
    report["hi"] = hi
    return report


def capture(*, client: Any, store: Any, symbol: str, timeframe: str,
            path: Path | None = None) -> Path:
    """Write one holdout snapshot through an already-connected client.

    Does not call initialize() or shutdown(). The trading process already
    holds the only bind, or the bot is stopped and this process is the only
    initialize. A second process would drop the live connection.

    Silent ``1.0`` (thin or unreadable histogram) is refused: that is the
    cheap-search path that hides the 18% gate. A **clamped** 1.0 is not
    the same number - ``_spread_scale`` floors a measured median under 1.0
    so the search never cheers cheaper than the bars. SpotBrent 24.08:
    n=309624, median 0.95, scale 1.0. Refusing that would permanently skip
    a symbol whose tick is tighter than the bar, which is a real market,
    not a bad read. GER40/NAS100 tonight measure 1.05 and still pass.
    """
    from .bar_snapshot import snapshot_path, write
    from .engine import (
        SPREAD_RATIO_BUCKETS,
        SPREAD_RATIO_MIN_SAMPLES,
        _ratio_percentile,
    )
    from .optimizer import Optimizer

    cfg = store.symbols.get(symbol)
    if cfg is None:
        raise ValueError(f"{symbol}: not in the store")
    info = client.info(symbol)
    if not info or not (float(info.get("point") or 0) > 0):
        raise ValueError(f"{symbol}: client.info missing point")
    opt = store.opt_params() or {}
    want = int(opt.get("max_bars") or 0) or 20000
    bars = client.bars(symbol, timeframe, want)
    if bars is None or len(bars) < 800:
        raise ValueError(f"{symbol}: bar window too short to be a holdout")
    min_stop = float(client.min_stop_distance(symbol))
    scaler = Optimizer(store=store, client=client)
    scale = float(scaler._spread_scale(symbol))
    if getattr(scaler, "_spread_scale_warned", False):
        # Except path returns 1.0 with the latch set. SpotBrent's floor is
        # also 1.0, so the numeric check below cannot tell them apart
        # (review 24.08 11:50). A fresh Optimizer starts unlatched; the
        # flag after this call is exactly "this read failed".
        raise ValueError(
            f"{symbol}: _spread_scale could not read the histogram - "
            "1.0 is not a measurement")
    blob = store.get_setting("spread_ratio", {}) or {}
    counts = blob.get(symbol) or []
    n = 0
    median = None
    if isinstance(counts, (list, tuple)):
        cleaned = [int(v) for v in counts
                   if isinstance(v, (int, float)) and not isinstance(v, bool)]
        n = sum(cleaned)
        if (len(cleaned) == SPREAD_RATIO_BUCKETS
                and n >= SPREAD_RATIO_MIN_SAMPLES):
            median = _ratio_percentile(cleaned, 0.50)
    if median is None or median <= 0:
        raise ValueError(
            f"{symbol}: spread_scale {scale} at capture - no measured median "
            f"(n={n}) - refusing the silent 1.0 that would hide the 18% gate")
    expected = float(min(5.0, max(1.0, median)))
    if abs(scale - expected) > 1e-9:
        # _spread_scale's except path returns 1.0 while this read of the same
        # blob still has a median. Writing that 1.0 would be the silent cheap
        # path the gate exists to stop (review 24.08 11:25).
        raise ValueError(
            f"{symbol}: measured median {median} -> {expected} expected, "
            f"_spread_scale returned {scale}")
    system = getattr(store, "system", None)
    dest = path or snapshot_path(symbol, timeframe)
    write(
        dest, symbol=symbol, timeframe=timeframe, bars=bars,
        info={
            "point": float(info.get("point") or 0),
            "tick_value": float(info.get("tick_value") or 0),
            "tick_size": float(info.get("tick_size") or 0),
        },
        min_stop=min_stop, spread_scale=scale, spread_scale_n=n,
        segments=int(opt.get("segments") or 0) or 5,
        trade_all_hours=bool(getattr(system, "trade_all_hours", False)),
        day_end_flatten_min=int(getattr(system, "day_end_flatten_min", 0) or 0),
        charge_costs=bool(getattr(system, "charge_costs", True)),
        max_cost_pct_of_risk=float(getattr(system, "max_cost_pct_of_risk", 0) or 0),
        config=cfg.to_dict(),
    )
    return dest


def capture_book(*, client: Any, store: Any) -> dict[str, Any]:
    """Pin every enabled symbol through the already-connected client.

    Does not initialize or shutdown. One symbol's failure is a WARN row, not
    a stop: a thin histogram on one name must not leave the rest of the book
    without a pin for the night.
    """
    rows: list[dict[str, Any]] = []
    symbols = getattr(store, "symbols", None) or {}
    if not isinstance(symbols, dict):
        symbols = {}
    for cfg in list(symbols.values()):
        if not getattr(cfg, "enabled", False):
            continue
        symbol = str(cfg.symbol)
        timeframe = str(cfg.timeframe)
        try:
            path = capture(client=client, store=store, symbol=symbol,
                           timeframe=timeframe)
            rows.append({"symbol": symbol, "ok": True, "path": str(path)})
            LOG.emit(f"Holdout snapshot yazildi | {symbol} {timeframe} | {path}", "OPT")
        except Exception as exc:
            rows.append({
                "symbol": symbol, "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            })
            LOG.emit(f"Holdout snapshot atlandi | {symbol}: {exc}", "WARN")
    n_ok = sum(1 for r in rows if r.get("ok"))
    return {"ok": True, "captured": n_ok, "results": rows}
