"""What the live config would have earned at a different entry-cost gate.

**This tool DESCRIBES the holdout. It does not choose.** It ranked on
holdout R/day and printed "en iyi kapi" until 11.09, and that is how
NAS100 got adx_min=10 / min_body_ratio=0.1 into a live config - the best
cell on the one slice it was ranked on, and worse than the incumbent on
the other four. The holdout is the referee; selecting on it consumes it.

Arm 1 of the 11.09 three-arm strategy review. The live record says the loss
is selectivity: split by MFE against each symbol's own lock threshold, 210 of
366 trades (57%) never move at all - net -160.17R at 10% winners - while the
156 that do move make +107.95R. And within each symbol (composition effect
removed), the expensive half of the trades is worse on three of four:

    XAUUSD  cheap +0.316R/trade  |  expensive -0.199R    <- cheap half PROFITS
    US30    cheap -0.174R        |  expensive -0.551R
    NAS100  cheap -0.244R        |  expensive -0.618R
    GER40   cheap -0.384R        |  expensive -0.087R    <- reversed

which reproduces the repo's own F49 finding. Meanwhile the live gates are
loose to the point of being inert: XAUUSD carries max_spread_atr=0.25 against
a median traded spread of 0.0144, seventeen times over.

The obvious next step is a search with the gate in the grid, and that is the
wrong measurement: it conflates the gate with whatever else the search finds
at that gate. This holds the live configuration completely fixed and varies
ONE axis, so the number is the gate's own effect.

``Params.from_config`` inherits every axis absent from the grid from the live
row (optimizer.py's own note), so a grid of ``{max_spread_atr: [v]}`` is
exactly "the live config, with the gate at v" - one combo, no search.

Offline and read-only throughout, same contract as ab_search.py and
m5_verdict.py: the archived holdout snapshots, no MT5, no live bot, no writes.

    python scripts/spread_gate_verdict.py --symbol XAUUSD
    python scripts/spread_gate_verdict.py --symbol US30 --gates 0.08,0.05,0.03
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from micofx.backtest import walk_forward  # noqa: E402
from micofx.bar_snapshot import read  # noqa: E402
from micofx.models import SymbolConfig  # noqa: E402
from micofx.mt5client import timeframe_seconds  # noqa: E402
from micofx.paths import DATA_DIR, DB_PATH, load_defaults  # noqa: E402

# Per axis, because "a gate" is not one scale. max_spread_atr is a share of
# ATR; atr_pct_min is a PERCENTILE (0-1) of the symbol's own ATR distribution -
# models.py calls it "ATR percentile floor", and the autopsy's ``atr_pct``
# (ATR/price, ~0.0017) is a different quantity with a confusingly similar
# name. Mixing them costs a factor of 150.
DEFAULT_GATES = {
    "max_spread_atr": (0.25, 0.15, 0.10, 0.08, 0.05, 0.03, 0.02, 0.015, 0.01),
    "atr_pct_min": (0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5),
    "adx_min": (0.0, 10.0, 15.0, 18.0, 20.0, 22.0, 25.0, 30.0),
    "min_body_ratio": (0.0, 0.1, 0.2, 0.3, 0.4, 0.5),
}


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
    for folder in (DATA_DIR / "holdout_bars",
                   DATA_DIR / "holdout_bars" / "_retired_M5"):
        path = folder / f"{safe}.npz"
        if path.exists():
            return read(path)
    raise SystemExit(f"snapshot yok: {safe}.npz")


def measure(cfg: SymbolConfig, snap: dict, opt: dict, gate: float,
            axis: str = "max_spread_atr") -> dict | None:
    """The live config on the holdout slice, with one axis pinned."""
    res = walk_forward(
        cfg=cfg, grid={axis: [gate]}, bars=snap["bars"],
        point=float(snap["info"]["point"]),
        tf_seconds=timeframe_seconds(cfg.timeframe),
        min_trades=int(opt["min_trades"]), segments=int(opt["segments"]),
        max_combos=1,
        min_positive_ratio=float(opt["min_positive_ratio"]),
        plateau_weight=float(opt["plateau_weight"]),
        refine_rounds=0,
        min_stop=float(snap["min_stop"]),
        all_hours=bool(snap["trade_all_hours"]),
        day_end_flatten_min=int(snap["day_end_flatten_min"]),
        spread_scale=float(snap["spread_scale"]),
        selection_metric=str(opt["selection_metric"]),
        combo_seed=7,
    )
    if not res.get("ok"):
        return {"error": str(res.get("error") or "aday yok"),
                "days": float(res.get("holdout_days") or 0.0)}
    hold = (res["best"].get("holdout") or {})
    days = float(res.get("holdout_days") or 0.0)
    net = float(hold.get("net_r") or 0.0)
    return {
        "net_r": net,
        "r_day": (net / days) if days > 0 else 0.0,
        "trades": int(hold.get("trades") or 0),
        "pf": float(hold.get("profit_factor") or 0.0),
        "dd": float(hold.get("max_dd_r") or 0.0),
        "days": days,
        "validated": bool(res.get("validated")),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--axis", default="max_spread_atr",
                    choices=sorted(DEFAULT_GATES),
                    help="which entry gate to sweep, one axis at a time")
    ap.add_argument("--gates", default="",
                    help="comma-separated values for that axis")
    ap.add_argument("--out", default="")
    args = ap.parse_args(argv)

    cfg = live_row(args.symbol)
    opt = live_opt_params()
    snap = snap_for(args.symbol, cfg.timeframe)
    gates = ([float(g) for g in args.gates.split(",") if g.strip()]
             if args.gates else list(DEFAULT_GATES[args.axis]))
    live_gate = float(getattr(cfg, args.axis, 0.0) or 0.0)
    if live_gate and live_gate not in gates:
        gates.append(live_gate)
    gates = sorted(set(gates), reverse=True)

    print(f"=== {args.symbol} {cfg.strategy}/{cfg.timeframe}  "
          f"canli {args.axis}={live_gate}", flush=True)
    print(f"{'kapi':>8} {'R/gun':>9} {'net R':>9} {'islem':>6} {'PF':>6} "
          f"{'dd':>7}  {'dogrulandi':>10}", flush=True)
    print("-" * 64, flush=True)

    out = {"symbol": args.symbol, "axis": args.axis, "live_gate": live_gate,
           "strategy": cfg.strategy, "timeframe": cfg.timeframe, "rows": []}
    for gate in gates:
        row = measure(cfg, snap, opt, gate, args.axis)
        mark = "  <-- CANLI" if abs(gate - live_gate) < 1e-9 else ""
        if row is None or "error" in row:
            print(f"{gate:>8.3f} {'-':>9} {'-':>9} {'-':>6} {'-':>6} {'-':>7}"
                  f"        RED: {(row or {}).get('error')}{mark}", flush=True)
            continue
        row["gate"] = gate
        out["rows"].append(row)
        print(f"{gate:>8.3f} {row['r_day']:>+9.4f} {row['net_r']:>+9.2f} "
              f"{row['trades']:>6} {row['pf']:>6.2f} {row['dd']:>7.1f}  "
              f"{'evet' if row['validated'] else 'hayir':>10}{mark}", flush=True)

    good = [r for r in out["rows"] if r["trades"] > 0]
    if good:
        # NOT max(r_day). This tool ranked on holdout R/day until 11.09 and
        # that is how NAS100 got adx_min=10 / min_body_ratio=0.1 written into
        # a live config: best on the holdout, WORSE on the other four slices
        # (validation +0.0808 against the incumbent's +0.1341, and negative on
        # one selection segment). Picking on the referee is the exact mistake
        # symbol_engine.py's docstring warns about, and this tool was the one
        # committing it. It now reports and does not choose.
        best = max(good, key=lambda r: r["r_day"])
        cur = next((r for r in good if abs(r["gate"] - live_gate) < 1e-9), None)
        print(flush=True)
        print(f"holdout'un en iyisi (SECIM DEGIL): {best['gate']:.3f} -> "
              f"{best['r_day']:+.4f} R/gun ({best['trades']} islem, "
              f"PF {best['pf']:.2f})")
        if cur:
            print(f"canli kapi : {cur['gate']:.3f} -> {cur['r_day']:+.4f} R/gun "
                  f"({cur['trades']} islem, PF {cur['pf']:.2f})")
            delta = best["r_day"] - cur["r_day"]
            print(f"fark       : {delta:+.4f} R/gun")
        print()
        print("UYARI: yukaridaki tablo holdout'u TARIF eder, bir secim degildir.")
        print("Holdout hakemdir; ona gore secmek onu tuketir. Bir degeri canliya")
        print("yazmadan once bes dilimin hepsinde olcun ve EN KOTU dilime bakin -")
        print("11.09'da bu tabloya bakip NAS100'e yazilan deger dort dilimde daha")
        print("kotuydu. Egri sekli de onemli: iki dusuk komsu arasindaki tek bir")
        print("sivri uc, kenar degil gurultudur.")
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
