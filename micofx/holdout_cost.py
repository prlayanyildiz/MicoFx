"""File-only holdout cost/R share. Does not import engine or mt5client.

``_holdout_costed`` stays the apply path and still talks to the bot's own
client. This module is the night measurement: same slice arithmetic, pinned
snapshot inputs, per-trade cost/R share against the live 18% gate.

Do not drop expensive trades and rescore. Live would have refused the fill,
so the rest of the sequence would have been different. Report the share.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import backtest
from .models import SymbolConfig
from .strategy import IndicatorCache, Params, compute

_TF_SECONDS = {"M5": 300, "M15": 900, "M30": 1800}


def _tf_seconds(name: str) -> int:
    key = str(name).upper()
    if key not in _TF_SECONDS:
        raise ValueError(f"unknown timeframe {name!r} - no silent M5 fallback")
    return _TF_SECONDS[key]


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
    edges = [int(round(n * i / segments)) for i in range(segments + 1)]
    lo, hi = edges[-2], edges[-1]
    cfg = SymbolConfig.from_dict(dict(snap["config"]))
    overlay = cfg.to_dict()
    overlay["timeframe"] = snap["timeframe"]
    overlay["symbol"] = snap["symbol"]
    tmp = SymbolConfig.from_dict(overlay)
    tf_seconds = _tf_seconds(snap["timeframe"])
    commission = backtest.commission_in_price(
        tmp.commission_per_lot,
        float(info.get("tick_value") or 0),
        float(info.get("tick_size") or 0),
    )
    scale = float(snap["spread_scale"])
    spread_pts = backtest.imputed_spread_pts(bars.spread)
    spread_price = spread_pts * point * scale
    raw_spread_price = spread_pts * point
    min_stop = float(snap["min_stop"])
    floor_const = backtest.stop_floor_const(min_stop, point)
    min_stop_series = np.maximum(floor_const, raw_spread_price * 1.5)
    tradable = backtest.session_mask(tmp, bars.time, bool(snap["trade_all_hours"]))
    flatten = backtest.flatten_mask(
        tmp, bars.time, bool(snap["trade_all_hours"]), int(snap["day_end_flatten_min"]))
    p = Params.from_config(tmp)
    cost_price = spread_price + float(commission)
    cache = IndicatorCache(bars.high, bars.low, bars.close, bars.time, tf_seconds,
                           bars.open, bars.volume, cost_price)
    sig = compute(cache, p)
    res = backtest.simulate(
        cache, sig, bars.open, bars.spread, point, p, tradable,
        lo, hi, commission,
        spread_price=spread_price, min_stop=min_stop_series, flatten=flatten,
        max_open=backtest.max_open_from_cfg(tmp),
        block_reverse=True)
    report = cost_share(res.trade_cost_rs, res.trade_rs, float(snap["max_cost_pct_of_risk"]))
    report["symbol"] = snap["symbol"]
    report["timeframe"] = snap["timeframe"]
    report["spread_scale"] = scale
    report["lo"] = lo
    report["hi"] = hi
    return report
