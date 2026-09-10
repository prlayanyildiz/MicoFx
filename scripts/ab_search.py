"""Compare two search setups on saved bars. No MT5, no live bot, no writes.

Built after a coverage argument nearly reshaped the live search grids on
arithmetic alone. The peer ACK that saved it asked for one thing - an A/B -
and the A/B refuted the proposal in twelve minutes. This is that A/B, made
repeatable, so the next idea gets measured before it gets ACK'd.

It reads a holdout snapshot (``data/bars/``) and the live symbol row, then
runs the real ``backtest.walk_forward`` with the real live ``opt_params``.
The only thing it varies is the grid. Read-only throughout: it opens the DB
in ``mode=ro`` and never POSTs anything.

    # is the live config beatable at all, on its own family?
    python scripts/ab_search.py --symbol GER40 --tf M30

    # every live family, ranked against the incumbent
    python scripts/ab_search.py --symbol GER40 --tf M30 --family all

    # what a grid change would do (the ACK-3 question)
    python scripts/ab_search.py --symbol GER40 --tf M30 --family all \\
        --drop-axes max_spread_atr,cost_rank_max,adx_min,min_body_ratio

Reading the output: ``taban`` is the live config replayed over the same
segments - the number a candidate has to beat. A candidate scoring under it
is the search saying "nothing better here", which is a different fact from
"the search could not look".

An axis dropped from the grid is NOT set to a default: ``Params.from_config``
inherits it from the live row. Dropping the gate axes therefore measures every
challenger family at the *incumbent* family's gates, which is exactly why that
proposal lost. Keep it in mind when reading a --drop-axes run.
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
if str(ROOT) not in sys.path:            # run-by-path needs the repo root
    sys.path.insert(0, str(ROOT))

from micofx.backtest import walk_forward  # noqa: E402
from micofx.bar_snapshot import read, snapshot_path  # noqa: E402
from micofx.models import SymbolConfig  # noqa: E402
from micofx.mt5client import timeframe_seconds  # noqa: E402
from micofx.paths import DB_PATH, load_defaults  # noqa: E402


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


def grid_size(grid: dict) -> int:
    n = 1
    for values in grid.values():
        n *= len(values)
    return n


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--tf", default="M30")
    ap.add_argument("--family", default="live",
                    help="'live' (the row's own), 'all', or a family name")
    ap.add_argument("--drop-axes", default="",
                    help="comma-separated axes to remove from the grid")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)

    path = snapshot_path(args.symbol, args.tf)
    if not path.exists():
        raise SystemExit(f"snapshot yok: {path}")
    snap = read(path)
    cfg = live_row(args.symbol)
    opt = live_opt_params()
    shipped = load_defaults()["optimizer"]

    if args.family == "live":
        families = [cfg.strategy]
    elif args.family == "all":
        families = list(opt.get("strategies") or shipped["strategies"])
    else:
        families = [args.family]

    drop = {a.strip() for a in args.drop_axes.split(",") if a.strip()}

    print(f"{args.symbol} {args.tf}  canli aile={cfg.strategy} "
          f"stamp={cfg.opt_score:.2f}  butce={opt['max_combos']} seed={args.seed}")
    if drop:
        print(f"izgaradan cikarilan eksenler: {sorted(drop)}")
        print("  (cikarilan eksen CANLI cfg'den miras alinir, varsayilana donmez)")
    print()
    print(f"{'aile':16} {'en iyi':>9} {'taban':>9} {'fark':>9} {'aday':>6} "
          f"{'izgara':>12} {'sn':>6}")
    print("-" * 76)

    # The incumbent's own number, measured with the live family in place. A
    # cross-family run swaps cfg.strategy, and walk_forward then reports a
    # baseline for *that* swap - the live parameters driving a family they were
    # never tuned for, which scores like nonsense (US30 burst params running
    # range_fade: -75.6). Comparing a challenger against that flatters it by
    # eighty points. The incumbent is measured once, unswapped, and every
    # challenger is compared to that.
    baseline = None
    if any(f != cfg.strategy for f in families):
        own = dict(shipped["strategy_grids"].get(cfg.strategy) or shipped["grid"])
        own = {k: v for k, v in own.items() if k not in drop}
        try:
            ref = run_one(cfg, args.tf, own, snap, opt, args.seed)
        except Exception as exc:                       # noqa: BLE001 - a tool
            raise SystemExit(f"incumbent taban olculemedi: {exc}") from exc
        if ref.get("baseline"):
            baseline = float(ref["baseline"].get("score") or 0.0)
        print(f"  incumbent taban ({cfg.strategy}, canli parametrelerle): "
              f"{baseline if baseline is not None else 'olculemedi'}")
        print()

    best_overall = (None, float("-inf"))
    for fam in families:
        grid = dict(shipped["strategy_grids"].get(fam) or shipped["grid"])
        grid = {k: v for k, v in grid.items() if k not in drop}
        run_cfg = copy.deepcopy(cfg)
        run_cfg.strategy = fam
        started = time.time()
        try:
            res = run_one(run_cfg, args.tf, grid, snap, opt, args.seed)
        except Exception as exc:                       # noqa: BLE001 - a tool
            print(f"{fam:16} HATA {exc}")
            continue
        secs = time.time() - started
        if baseline is None and res.get("baseline") and fam == cfg.strategy:
            baseline = float(res["baseline"].get("score") or 0.0)
        if not res.get("ok"):
            print(f"{fam:16} {'-':>9} {'-':>9} {'-':>9} {'-':>6} "
                  f"{grid_size(grid):12,} {secs:6.0f}   "
                  f"RED: {res.get('error') or 'aday yok'}")
            continue
        score = float(res["best"]["score"])
        base = baseline if baseline is not None else 0.0
        if score > best_overall[1]:
            best_overall = (fam, score)
        print(f"{fam:16} {score:9.3f} {base:9.3f} {score - base:+9.3f} "
              f"{res['candidates']:6} {grid_size(grid):12,} {secs:6.0f}")

    print()
    fam, score = best_overall
    if fam is None or baseline is None:
        print("sonuc yok")
        return 0
    if score > baseline:
        print(f"KAZANAN: {fam} {score:.3f} > taban {baseline:.3f} "
              f"(+{score - baseline:.3f}) - aday var")
    else:
        print(f"TABAN YENILMEDI: en iyi {fam} {score:.3f} < taban {baseline:.3f}. "
              f"Arama 'bulamiyor' degil, 'daha iyisi yok' diyor olabilir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
