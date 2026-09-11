"""Re-measure M5 against the live bar, on the number the record demands.

M5 was retired 05.09. ``models.py`` states the verdict and the terms of appeal
in the same breath: *"the reason to reopen it is an R/day number"*. The verdict
itself was: 0 of 7 symbols would pick M5, five outright negative, and the two
that were not (GER40 +6.4, US30 +10.2) *"sit far under their live bar"*.

That last clause is why this exists. "Their live bar" was
``cfg.opt_summary["holdout"]`` - the stamp that 10-11.09 showed to be four to
five times what an incumbent actually delivers on the slice being compared. So
half the M5 verdict rested on a comparison that has since been shown wrong,
and the book has also gained two families (``range_fade``, ``sweep_fade``) it
did not have on 05.09.

This settles it with a measurement instead of an argument. Fully offline: the
M5 snapshots were archived rather than deleted (``holdout_bars/_retired_M5``),
so no MT5 call, no live bot, no DB write - the same read-only contract as
``ab_search.py``.

Per symbol it runs the same walk-forward on both bars, same budget, same live
``opt_params``, every living family, and reports holdout **R per day** - the
only honest cross-timeframe unit, since 90k M5 bars span a year where 90k M30
bars span several.

    python scripts/m5_verdict.py --symbol GER40
    python scripts/m5_verdict.py --symbol NAS100 --families live
"""
from __future__ import annotations

import argparse
import copy
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from micofx.backtest import walk_forward  # noqa: E402
from micofx.bar_snapshot import read  # noqa: E402
from micofx.models import SymbolConfig  # noqa: E402
from micofx.mt5client import timeframe_seconds  # noqa: E402
from micofx.paths import DATA_DIR, DB_PATH, load_defaults  # noqa: E402

# Archived, not deleted - which is the only reason this can be answered
# without asking the terminal for a year of M5 bars.
RETIRED_M5_DIR = DATA_DIR / "holdout_bars" / "_retired_M5"
LIVE_DIR = DATA_DIR / "holdout_bars"


def _ro_db() -> sqlite3.Connection:
    """Read-only: the live process owns this file (AGENTS.md)."""
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10.0)


def live_row(symbol: str) -> SymbolConfig:
    with _ro_db() as db:
        row = db.execute(
            "SELECT payload FROM symbols WHERE symbol=?", (symbol,)).fetchone()
    if not row:
        raise SystemExit(f"{symbol} kitapta yok")
    return SymbolConfig.from_dict(json.loads(row[0]))


def live_opt_params() -> dict:
    with _ro_db() as db:
        row = db.execute(
            "SELECT value FROM settings WHERE key='opt_params'").fetchone()
    shipped = load_defaults()["optimizer"]
    return {**shipped, **(json.loads(row[0]) if row else {})}


def snap_for(symbol: str, tf: str) -> dict:
    safe = "".join(ch if ch.isalnum() else "_" for ch in f"{symbol}_{tf}")
    for folder in (LIVE_DIR, RETIRED_M5_DIR):
        path = folder / f"{safe}.npz"
        if path.exists():
            return read(path)
    raise SystemExit(f"snapshot yok: {safe}.npz")


def run_one(cfg: SymbolConfig, tf: str, grid: dict, snap: dict, opt: dict,
            seed: int) -> dict:
    return walk_forward(
        cfg=cfg, grid=grid, bars=snap["bars"],
        point=float(snap["info"]["point"]), tf_seconds=timeframe_seconds(tf),
        min_trades=int(opt["min_trades"]), segments=int(opt["segments"]),
        max_combos=int(opt["max_combos"]),
        min_positive_ratio=float(opt["min_positive_ratio"]),
        plateau_weight=float(opt["plateau_weight"]),
        refine_rounds=int(opt["refine_rounds"]),
        min_stop=float(snap["min_stop"]),
        all_hours=bool(snap["trade_all_hours"]),
        day_end_flatten_min=int(snap["day_end_flatten_min"]),
        spread_scale=float(snap["spread_scale"]),
        selection_metric=str(opt["selection_metric"]),
        combo_seed=seed,
    )


def _per_day(block: dict, days: float) -> float:
    if days <= 0:
        return 0.0
    return float(block.get("net_r") or 0.0) / days


def measure(symbol: str, tf: str, families: list[str], opt: dict,
            shipped: dict, seed: int) -> dict:
    """Every family on one bar. Returns the best by holdout R/day, plus the
    incumbent's own holdout on that bar for reference."""
    cfg = live_row(symbol)
    snap = snap_for(symbol, tf)
    out: dict = {"tf": tf, "rows": [], "best": None, "baseline": None,
                 "days": 0.0, "bars": len(snap["bars"])}
    for fam in families:
        grid = dict(shipped["strategy_grids"].get(fam) or shipped["grid"])
        run_cfg = copy.deepcopy(cfg)
        run_cfg.strategy = fam
        started = time.time()
        try:
            res = run_one(run_cfg, tf, grid, snap, opt, seed)
        except Exception as exc:                       # noqa: BLE001 - a tool
            print(f"  {tf:<4} {fam:<15} HATA {exc}", flush=True)
            continue
        secs = time.time() - started
        days = float(res.get("holdout_days") or 0.0)
        out["days"] = days or out["days"]
        # The incumbent measured on this bar: walk_forward's own baseline,
        # which for the live family is the live config itself.
        base = (res.get("baseline") or {}).get("holdout") or {}
        if fam == cfg.strategy and base:
            out["baseline"] = {"net_r": float(base.get("net_r") or 0.0),
                               "r_day": _per_day(base, days),
                               "trades": int(base.get("trades") or 0),
                               "pf": float(base.get("profit_factor") or 0.0)}
        if not res.get("ok"):
            print(f"  {tf:<4} {fam:<15} RED: {res.get('error') or 'aday yok'} "
                  f"({secs:.0f}s)", flush=True)
            continue
        hold = res["best"].get("holdout") or {}
        row = {
            "family": fam,
            "net_r": float(hold.get("net_r") or 0.0),
            "r_day": _per_day(hold, days),
            "trades": int(hold.get("trades") or 0),
            "pf": float(hold.get("profit_factor") or 0.0),
            "dd": float(hold.get("max_dd_r") or 0.0),
            "score": float(res["best"].get("score") or 0.0),
            "validated": bool(res.get("validated")),
            "pos_ratio": res["best"].get("positive_ratio"),
            "days": days,
        }
        out["rows"].append(row)
        flag = "" if row["validated"] else "  (dogrulanmadi)"
        print(f"  {tf:<4} {fam:<15} R/gun {row['r_day']:+7.4f}  "
              f"net {row['net_r']:+8.2f}R  PF {row['pf']:.2f}  "
              f"n={row['trades']:<5} dd={row['dd']:.1f}  {secs:.0f}s{flag}",
              flush=True)
    live = [r for r in out["rows"] if r["validated"]]
    if live:
        out["best"] = max(live, key=lambda r: r["r_day"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--families", default="all",
                    help="'all', 'live', or a comma-separated list")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="", help="write the result as JSON here")
    args = ap.parse_args(argv)

    opt = live_opt_params()
    shipped = load_defaults()["optimizer"]
    cfg = live_row(args.symbol)
    if args.families == "all":
        families = list(opt.get("strategies") or shipped["strategies"])
    elif args.families == "live":
        families = [cfg.strategy]
    else:
        families = [f.strip() for f in args.families.split(",") if f.strip()]

    print(f"=== {args.symbol}  canli {cfg.strategy}/{cfg.timeframe}  "
          f"butce={opt['max_combos']}x{1 + int(opt['refine_rounds'])} "
          f"seed={args.seed} aileler={len(families)}", flush=True)

    result = {"symbol": args.symbol, "live_family": cfg.strategy,
              "live_tf": cfg.timeframe, "sides": {}}
    for tf in ("M5", cfg.timeframe):
        side = measure(args.symbol, tf, families, opt, shipped, args.seed)
        result["sides"][tf] = side
        if side["best"]:
            b = side["best"]
            print(f"  -> {tf} en iyi: {b['family']} {b['r_day']:+.4f} R/gun "
                  f"({b['days']:.0f} gun)", flush=True)
        else:
            print(f"  -> {tf}: dogrulanmis aday yok", flush=True)
        print(flush=True)

    m5 = result["sides"]["M5"]["best"]
    live = result["sides"][cfg.timeframe]["best"]
    base = result["sides"][cfg.timeframe].get("baseline")
    print(f"--- {args.symbol} KARAR")
    if base:
        print(f"    yururlukteki  {cfg.strategy}/{cfg.timeframe} "
              f"{base['r_day']:+.4f} R/gun ({base['net_r']:+.1f}R, "
              f"PF {base['pf']:.2f}, n={base['trades']})")
    print(f"    en iyi M5     "
          f"{m5['family'] + ' ' + format(m5['r_day'], '+.4f') + ' R/gun' if m5 else 'yok'}")
    print(f"    en iyi {cfg.timeframe:<6}"
          f"{live['family'] + ' ' + format(live['r_day'], '+.4f') + ' R/gun' if live else 'yok'}")
    if m5 and live:
        verdict = "M5 KAZANIYOR" if m5["r_day"] > live["r_day"] else "M5 kaybediyor"
        print(f"    {verdict}: {m5['r_day']:+.4f} vs {live['r_day']:+.4f} R/gun")
    elif m5 and not live:
        print("    M5'te aday var, canli barda yok")
    else:
        print("    M5'te dogrulanmis aday yok")

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"    JSON: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
