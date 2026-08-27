"""Persist holdout bar windows so a cost/R replay does not touch MT5.

The live bot holds the only initialize() on this terminal. A second one
would shutdown() the trading process. The holdout slice is historical and
does not change, so the bars need fetching once, then every measurement
reads the file.

Fetch itself is not this module: that waits for a window with no session
(00:00 after gece_restart, or the bot stopped). This is only the on-disk
shape _bars_for_holdout already produces in memory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .bars import Bars
from .paths import DATA_DIR

# Copied from engine.SPREAD_RATIO_MIN_SAMPLES. Do not import engine here:
# that module pulls MetaTrader5 (review 24.08 09:00). A test asserts they
# stay equal. The silent 1.0 this floor refuses lives in _spread_scale.
SPREAD_RATIO_MIN_SAMPLES = 400

SNAPSHOT_VERSION = 3
SNAPSHOT_DIR = DATA_DIR / "holdout_bars"


def snapshot_path(symbol: str, timeframe: str) -> Path:
    safe = "".join(ch if ch.isalnum() else "_" for ch in f"{symbol}_{timeframe}")
    return SNAPSHOT_DIR / f"{safe}.npz"


def write(path: Path, *, symbol: str, timeframe: str, bars: Bars,
          info: dict[str, Any], min_stop: float,
          spread_scale: float, spread_scale_n: int,
          segments: int, trade_all_hours: bool, day_end_flatten_min: int,
          charge_costs: bool, max_cost_pct_of_risk: float,
          config: dict[str, Any]) -> None:
    """Persist bars plus the cost inputs a replay must not re-read live.

    ``spread_scale`` is the live-tick/bar median at fetch time. Leaving it
    out meant the same file, a week later, would multiply cost/R by a
    different histogram (review 24.08 08:55). Replay must not call
    ``_spread_scale``: that helper returns 1.0 on failure, which shrinks
    cost/R and hides the 18% live refusals this measurement exists to count.

    Version 3 also pins the store-side knobs (Claude 24.08 09:15). They are
    not MT5, but ``segments`` moves the holdout edges and ``charge_costs``
    off zeros the spread - same file, different number, without them.
    """
    scale = float(spread_scale)
    n = int(spread_scale_n)
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError(f"spread_scale must be a positive finite, got {spread_scale!r}")
    if n < SPREAD_RATIO_MIN_SAMPLES:
        raise ValueError(
            f"spread_scale_n {n} < {SPREAD_RATIO_MIN_SAMPLES} - refusing a "
            "thin histogram that _spread_scale would silently call 1.0")
    # charge_costs=False is a live operator choice (this book: commission 0,
    # trail holds through the spread). Refusing the file used to skip all six
    # names at gece capture (27.08 00:00, 0 yazildi). Stamp the real flag so
    # the file records the regime it was captured under. Nothing reads it
    # back today — this is archive metadata, not a gate.
    segs = int(segments)
    if segs < 2:
        raise ValueError(f"segments must be >= 2, got {segments!r}")
    threshold = float(max_cost_pct_of_risk)
    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError(f"max_cost_pct_of_risk must be >= 0, got {max_cost_pct_of_risk!r}")
    # 0 is a live operator choice (block_high_cost off). Refusing it used to
    # skip the night pin the same way charge_costs=False did on 27.08 00:00.
    if not isinstance(config, dict) or not config:
        raise ValueError("config must be a non-empty dict (SymbolConfig.to_dict)")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        version=np.int32(SNAPSHOT_VERSION),
        symbol=np.asarray(symbol),
        timeframe=np.asarray(timeframe),
        time=np.asarray(bars.time, dtype=np.int64),
        open=np.asarray(bars.open, dtype=np.float64),
        high=np.asarray(bars.high, dtype=np.float64),
        low=np.asarray(bars.low, dtype=np.float64),
        close=np.asarray(bars.close, dtype=np.float64),
        spread=np.asarray(bars.spread, dtype=np.float64),
        volume=np.asarray(bars.volume, dtype=np.float64),
        forming_time=np.int64(bars.forming_time),
        point=np.float64(info.get("point") or 0.0),
        tick_value=np.float64(info.get("tick_value") or 0.0),
        tick_size=np.float64(info.get("tick_size") or 0.0),
        min_stop=np.float64(min_stop),
        spread_scale=np.float64(scale),
        spread_scale_n=np.int64(n),
        segments=np.int32(segs),
        trade_all_hours=np.bool_(bool(trade_all_hours)),
        day_end_flatten_min=np.int32(int(day_end_flatten_min)),
        charge_costs=np.bool_(bool(charge_costs)),
        max_cost_pct_of_risk=np.float64(threshold),
        config_json=np.asarray(json.dumps(config, default=str)),
    )


def read(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as blob:
        if int(blob["version"]) != SNAPSHOT_VERSION:
            raise ValueError(f"holdout bar snapshot version {int(blob['version'])}")
        n = int(blob["time"].size)
        rates = np.zeros(n, dtype=[
            ("time", np.int64), ("open", np.float64), ("high", np.float64),
            ("low", np.float64), ("close", np.float64), ("spread", np.float64),
            ("tick_volume", np.float64),
        ])
        rates["time"] = blob["time"]
        rates["open"] = blob["open"]
        rates["high"] = blob["high"]
        rates["low"] = blob["low"]
        rates["close"] = blob["close"]
        rates["spread"] = blob["spread"]
        rates["tick_volume"] = blob["volume"]
        bars = Bars(rates, int(blob["forming_time"]))
        config = json.loads(str(blob["config_json"]))
        if not isinstance(config, dict) or not config:
            raise ValueError("holdout bar snapshot config_json is not an object")
        return {
            "symbol": str(blob["symbol"]),
            "timeframe": str(blob["timeframe"]),
            "bars": bars,
            "info": {
                "point": float(blob["point"]),
                "tick_value": float(blob["tick_value"]),
                "tick_size": float(blob["tick_size"]),
            },
            "min_stop": float(blob["min_stop"]),
            "spread_scale": float(blob["spread_scale"]),
            "spread_scale_n": int(blob["spread_scale_n"]),
            "segments": int(blob["segments"]),
            "trade_all_hours": bool(np.asarray(blob["trade_all_hours"]).item()),
            "day_end_flatten_min": int(blob["day_end_flatten_min"]),
            "charge_costs": bool(np.asarray(blob["charge_costs"]).item()),
            "max_cost_pct_of_risk": float(blob["max_cost_pct_of_risk"]),
            "config": config,
        }
