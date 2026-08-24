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

from pathlib import Path
from typing import Any

import numpy as np

from .mt5client import Bars
from .paths import DATA_DIR

SNAPSHOT_VERSION = 1
SNAPSHOT_DIR = DATA_DIR / "holdout_bars"


def snapshot_path(symbol: str, timeframe: str) -> Path:
    safe = "".join(ch if ch.isalnum() else "_" for ch in f"{symbol}_{timeframe}")
    return SNAPSHOT_DIR / f"{safe}.npz"


def write(path: Path, *, symbol: str, timeframe: str, bars: Bars,
          info: dict[str, Any], min_stop: float) -> None:
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
        }
