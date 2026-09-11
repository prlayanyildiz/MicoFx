"""Build one symbol its own engine, by walking its space instead of sampling it.

Operator, 11.09: "sembole has motor kur, o sembol ozelinde kanitlanms olani,
ve darbogazsiz olsun".

The bottleneck is measured and it is not the families. XAUUSD's mtf_pullback
grid holds **4,790,016,000** combinations and ``max_combos`` is 2000 - four
ten-millionths of a percent. At that ratio the search cannot find a specific
pairing of two axes, which is why two hand-tried values on NAS100 beat
everything it had found: I looked directly instead of sampling.

Coordinate descent walks the same space in ``axes x values x passes`` instead.
Pin every axis but one, sweep that one, keep the winner, move to the next, and
repeat until a whole pass changes nothing. Fifteen axes at five values over
two passes is 150 evaluations - not two thousand, and not four billion.

**It ranks on the selection score, never on holdout.** Picking by holdout is
how a lone spike gets installed: GER40's ``min_body_ratio`` measured 0.0758 at
0.4 with 0.0678 and 0.0676 on either side of it, on a 247-trade sample, and I
applied it before reading the curve. ``walk_forward``'s own score already
carries the selection segment and the plateau weighting that exists to refuse
exactly that shape. Holdout stays the referee it was designed to be: untouched
during the walk, reported at the end, and a candidate that does not clear
``validated`` is not a candidate.

Offline and read-only, same contract as the other measurement tools here: the
archived snapshots, no MT5, no live bot, no writes.

    python scripts/symbol_engine.py --symbol NAS100
    python scripts/symbol_engine.py --symbol GER40 --family super_trend
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from gate_verdict import live_opt_params, live_row, snap_for  # noqa: E402

from micofx.backtest import walk_forward  # noqa: E402
from micofx.models import SymbolConfig  # noqa: E402
from micofx.mt5client import timeframe_seconds  # noqa: E402
from micofx.paths import load_defaults  # noqa: E402


def axes_for(family: str, opt: dict, shipped: dict) -> dict[str, list]:
    """Every axis this family can actually be tuned on, shared grid included."""
    grid: dict[str, list] = {}
    for source in (shipped.get("grid") or {}, opt.get("grid") or {}):
        for axis, values in source.items():
            if isinstance(values, list) and values:
                grid[axis] = list(values)
    for source in (shipped.get("strategy_grids") or {},
                   opt.get("strategy_grids") or {}):
        for axis, values in (source.get(family) or {}).items():
            if isinstance(values, list) and values:
                grid[axis] = list(values)
    return grid


def evaluate(cfg: SymbolConfig, snap: dict, opt: dict,
             pinned: dict[str, Any]) -> dict[str, Any] | None:
    """One combination: every axis pinned to a single value, no search."""
    grid = {axis: [value] for axis, value in pinned.items()}
    res = walk_forward(
        cfg=cfg, grid=grid, bars=snap["bars"],
        point=float(snap["info"]["point"]),
        tf_seconds=timeframe_seconds(cfg.timeframe),
        min_trades=int(opt["min_trades"]), segments=int(opt["segments"]),
        max_combos=1, min_positive_ratio=float(opt["min_positive_ratio"]),
        plateau_weight=float(opt["plateau_weight"]), refine_rounds=0,
        min_stop=float(snap["min_stop"]), all_hours=bool(snap["trade_all_hours"]),
        day_end_flatten_min=int(snap["day_end_flatten_min"]),
        spread_scale=float(snap["spread_scale"]),
        selection_metric=str(opt["selection_metric"]), combo_seed=7)
    if not res.get("ok"):
        return None
    best = res["best"]
    hold = best.get("holdout") or {}
    days = float(res.get("holdout_days") or 0.0)
    return {
        "score": float(best.get("score") or 0.0),      # what we rank on
        "validated": bool(res.get("validated")),
        "hold_net": float(hold.get("net_r") or 0.0),   # referee, never ranked on
        "hold_r_day": (float(hold.get("net_r") or 0.0) / days) if days else 0.0,
        "hold_pf": float(hold.get("profit_factor") or 0.0),
        "hold_n": int(hold.get("trades") or 0),
        "hold_dd": float(hold.get("max_dd_r") or 0.0),
    }


def descend(sym: str, family: str, passes: int = 2) -> dict[str, Any]:
    cfg = live_row(sym)
    if family:
        cfg = copy.deepcopy(cfg)
        cfg.strategy = family
    fam = str(cfg.strategy)
    opt = live_opt_params()
    shipped = load_defaults()["optimizer"]
    snap = snap_for(sym, cfg.timeframe)
    grid = axes_for(fam, opt, shipped)

    # Start where the symbol already is: its own live value on every axis the
    # grid can move. That way the walk can only report an improvement over
    # what is running, never over some arbitrary starting point.
    # Keep each axis's own type. Coercing everything to float breaks the
    # integer axes: `mtf_pullback` derives `warmup` from `htf_factor` and
    # `pull_fast`, and a float warmup raises on `buy[:warmup]`. The grid
    # already ships the right type for every value, so the starting point
    # takes its type from the grid rather than from float().
    pinned: dict[str, Any] = {}
    for axis, values in grid.items():
        cur = getattr(cfg, axis, None)
        if cur is None:
            continue
        caster = int if all(isinstance(v, int) for v in values) else float
        try:
            pinned[axis] = caster(cur)
        except (TypeError, ValueError):
            continue
    if not pinned:
        raise SystemExit(f"{sym}/{fam}: ayarlanabilir eksen yok")

    start = evaluate(cfg, snap, opt, pinned)
    if start is None:
        raise SystemExit(f"{sym}/{fam}: baslangic konfigurasyonu olculemedi")
    print(f"=== {sym} {fam}/{cfg.timeframe}  {len(pinned)} eksen, {passes} gecis",
          flush=True)
    print(f"    baslangic (canli degerler): skor {start['score']:.3f}  "
          f"holdout {start['hold_r_day']:+.4f} R/gun  n={start['hold_n']}  "
          f"PF {start['hold_pf']:.2f}", flush=True)

    best = dict(start)
    evals = 1
    for p in range(1, passes + 1):
        moved = False
        for axis in sorted(pinned):
            options = [v for v in grid[axis]
                       if abs(float(v) - float(pinned[axis])) > 1e-12]
            for value in options:
                trial = dict(pinned)
                trial[axis] = value          # the grid's own type, not float
                got = evaluate(cfg, snap, opt, trial)
                evals += 1
                if got is None or not got["validated"]:
                    continue
                if got["score"] > best["score"] + 1e-9:
                    was = pinned[axis]
                    pinned[axis] = value
                    best = got
                    moved = True
                    print(f"    gecis {p}: {axis} {was:g} -> {value:g}  "
                          f"skor {got['score']:.3f}  "
                          f"holdout {got['hold_r_day']:+.4f} R/gun", flush=True)
        if not moved:
            print(f"    gecis {p}: degisiklik yok - durdu", flush=True)
            break

    changed = {a: v for a, v in pinned.items()
               if abs(float(getattr(cfg, a, 0) or 0) - v) > 1e-12}
    print(flush=True)
    print(f"    {evals} degerlendirme", flush=True)
    print(f"    SONUC  skor {start['score']:.3f} -> {best['score']:.3f}", flush=True)
    print(f"           holdout {start['hold_r_day']:+.4f} -> {best['hold_r_day']:+.4f} "
          f"R/gun  ({start['hold_net']:+.1f}R -> {best['hold_net']:+.1f}R)", flush=True)
    print(f"           PF {start['hold_pf']:.2f} -> {best['hold_pf']:.2f}   "
          f"n {start['hold_n']} -> {best['hold_n']}   "
          f"dd {start['hold_dd']:.1f} -> {best['hold_dd']:.1f}", flush=True)
    print(f"           degisen eksenler: {changed or 'yok'}", flush=True)
    return {"symbol": sym, "family": fam, "timeframe": cfg.timeframe,
            "start": start, "best": best, "changed": changed, "evals": evals}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--family", default="", help="default: the symbol's live family")
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    started = time.time()
    out = descend(args.symbol, args.family, args.passes)
    out["elapsed_sec"] = round(time.time() - started, 1)
    print(f"           {out['elapsed_sec']:.0f} saniye", flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
