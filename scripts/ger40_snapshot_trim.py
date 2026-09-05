"""Trim GER40 (or any) holdout snapshot dirty head — missing-spread junk.

Claude 15:24/16:14/16:38: GER40 M30 first ~23% has no raw spread; imputed
cost invents a fake 6/6. Rolling 500-bar miss-rate <5% lands ~2020-07.

File-only (no MT5). Does not unfreeze. Backup ``.npz.bak`` before apply.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from micofx.bar_snapshot import read, snapshot_path, write
from micofx.bars import Bars
from micofx.holdout_cost import MIN_CAPTURE_BARS

_MIN_BARS = int(MIN_CAPTURE_BARS)
ROLL_WIN = 500
MAX_MISS = 0.05


def find_clean_start(
    spread: np.ndarray,
    *,
    roll_win: int = ROLL_WIN,
    max_miss: float = MAX_MISS,
) -> int | None:
    """First index where the next ``roll_win`` bars have miss-rate < max_miss."""
    sp = np.asarray(spread, dtype=np.float64)
    if len(sp) < int(roll_win) + 40:
        return None
    miss = (~np.isfinite(sp)) | (sp <= 0.0)
    w = int(roll_win)
    for i in range(0, len(sp) - w + 1):
        if float(miss[i:i + w].mean()) < float(max_miss):
            return int(i)
    return None


def trim_snapshot(
    path: Path,
    *,
    apply: bool = False,
    roll_win: int = ROLL_WIN,
    max_miss: float = MAX_MISS,
    min_bars: int = _MIN_BARS,
) -> dict[str, Any]:
    """Dry-run or rewrite snapshot from clean start. Returns a report dict."""
    snap = read(path)
    bars = snap["bars"]
    cut = find_clean_start(bars.spread, roll_win=roll_win, max_miss=max_miss)
    n = len(bars.time)
    if cut is None:
        return {"ok": False, "error": "clean start not found", "n": n, "path": str(path)}
    remain = n - cut
    if remain < int(min_bars):
        return {
            "ok": False,
            "error": f"remain {remain} < min_bars {min_bars}",
            "cut": cut, "n": n, "path": str(path),
        }
    report: dict[str, Any] = {
        "ok": True,
        "path": str(path),
        "n_before": n,
        "cut": cut,
        "cut_time": int(bars.time[cut]),
        "n_after": remain,
        "applied": False,
    }
    if not apply:
        report["note"] = "dry-run — pass --apply to rewrite (writes .npz.bak first)"
        return report
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    # Slice into a new Bars via structured array (same shape write() expects).
    rates = np.zeros(remain, dtype=[
        ("time", np.int64), ("open", np.float64), ("high", np.float64),
        ("low", np.float64), ("close", np.float64), ("spread", np.float64),
        ("tick_volume", np.float64),
    ])
    rates["time"] = bars.time[cut:]
    rates["open"] = bars.open[cut:]
    rates["high"] = bars.high[cut:]
    rates["low"] = bars.low[cut:]
    rates["close"] = bars.close[cut:]
    rates["spread"] = bars.spread[cut:]
    rates["tick_volume"] = bars.volume[cut:]
    new_bars = Bars(rates, int(bars.forming_time))
    write(
        path,
        symbol=str(snap["symbol"]),
        timeframe=str(snap["timeframe"]),
        bars=new_bars,
        info=dict(snap["info"]),
        min_stop=float(snap["min_stop"]),
        spread_scale=float(snap["spread_scale"]),
        spread_scale_n=int(snap["spread_scale_n"]),
        segments=int(snap["segments"]),
        trade_all_hours=bool(snap["trade_all_hours"]),
        day_end_flatten_min=int(snap["day_end_flatten_min"]),
        charge_costs=bool(snap["charge_costs"]),
        max_cost_pct_of_risk=float(snap["max_cost_pct_of_risk"]),
        config=dict(snap["config"]),
    )
    report["applied"] = True
    report["backup"] = str(bak)
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Trim dirty holdout snapshot head")
    p.add_argument("--symbol", default="GER40")
    p.add_argument("--timeframe", default="M30")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    path = snapshot_path(args.symbol, args.timeframe)
    if not path.is_file():
        print(f"missing {path}")
        return 1
    rep = trim_snapshot(path, apply=bool(args.apply))
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
