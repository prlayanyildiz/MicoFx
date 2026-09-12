"""Autopsy: first ticket vs scale-in bleed (read-only).

A fill that opens while another ticket on the same symbol is still open
counts as scale-in. Reports net R split and the counterfactual book if
those scale-ins never opened.

    python scripts/scale_in_bleed.py
    python scripts/scale_in_bleed.py --symbols GER40,NAS100,XAUUSD
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.panel_session import opener as _panel_opener  # noqa: E402

PANEL = "http://127.0.0.1:8900"
LIVE_DEFAULT = ("GER40", "NAS100", "XAUUSD")
OUT = ROOT / ".bridge" / "SCALE_IN_BLEED.json"


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _ts(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        v = row.get(key)
        if v is None or v == "":
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def classify_scale_ins(
    rows: list[dict[str, Any]],
    *,
    symbols: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Split closed trades into first-leg vs scale-in by open overlap."""
    by_sym: dict[str, list[dict[str, Any]]] = {}
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        sym = str(r.get("symbol") or "").strip()
        if not sym:
            continue
        if symbols is not None and sym not in symbols:
            continue
        by_sym.setdefault(sym, []).append(r)

    per: dict[str, Any] = {}
    first_n = scale_n = 0
    first_r = scale_r = 0.0
    for sym, items in sorted(by_sym.items()):
        ordered = sorted(
            items,
            key=lambda r: (_ts(r, "fill_time", "open_time") or 0.0,
                           _ts(r, "exit_time", "close_time") or 0.0),
        )
        open_exits: list[float] = []
        first_rows: list[dict[str, Any]] = []
        scale_rows: list[dict[str, Any]] = []
        for r in ordered:
            fill = _ts(r, "fill_time", "open_time")
            exit_t = _ts(r, "exit_time", "close_time")
            if fill is None or exit_t is None:
                continue
            open_exits = [x for x in open_exits if x > fill]
            bucket = scale_rows if open_exits else first_rows
            bucket.append(r)
            open_exits.append(exit_t)

        def _sum_r(xs: list[dict[str, Any]]) -> float:
            return sum(_f(r.get("r_realised")) for r in xs)

        fr = _sum_r(first_rows)
        sr = _sum_r(scale_rows)
        first_n += len(first_rows)
        scale_n += len(scale_rows)
        first_r += fr
        scale_r += sr
        total = len(first_rows) + len(scale_rows)
        per[sym] = {
            "n": total,
            "first_n": len(first_rows),
            "first_net_r": round(fr, 4),
            "scale_n": len(scale_rows),
            "scale_net_r": round(sr, 4),
            "scale_share_pct": round(100.0 * len(scale_rows) / total, 1) if total else 0.0,
            "counterfactual_net_r": round(fr, 4),
            "live_net_r": round(fr + sr, 4),
        }

    live = first_r + scale_r
    return {
        "symbols": per,
        "totals": {
            "first_n": first_n,
            "first_net_r": round(first_r, 4),
            "scale_n": scale_n,
            "scale_net_r": round(scale_r, 4),
            "live_net_r": round(live, 4),
            "counterfactual_net_r": round(first_r, 4),
            "scale_bleed_r": round(scale_r, 4),
            "scale_bleed_pct_of_loss": (
                round(100.0 * abs(scale_r) / abs(live), 1)
                if live < 0 and scale_r < 0 else None
            ),
        },
    }


def fetch_autopsies(panel: str = PANEL) -> list[dict[str, Any]]:
    op = _panel_opener(panel)
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/analysis/trade-autopsies",
                headers={"Origin": panel},
            ),
            timeout=30,
        ).read().decode()
    )
    rows = body.get("rows") or []
    return list(rows) if isinstance(rows, list) else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--panel", default=PANEL)
    ap.add_argument(
        "--symbols",
        default=",".join(LIVE_DEFAULT),
        help="Comma list; empty = all symbols in autopsy",
    )
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    syms = frozenset(s.strip() for s in args.symbols.split(",") if s.strip())
    rows = fetch_autopsies(args.panel)
    report = classify_scale_ins(rows, symbols=syms or None)
    report["n_rows_scanned"] = len(rows)
    report["filter"] = sorted(syms) if syms else "all"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    tot = report["totals"]
    print(
        f"scale-in bleed: {tot['scale_n']} trades {tot['scale_net_r']}R "
        f"(live {tot['live_net_r']}R -> first-only {tot['counterfactual_net_r']}R)",
        flush=True,
    )
    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
