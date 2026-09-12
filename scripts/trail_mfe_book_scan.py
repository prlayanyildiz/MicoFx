"""Offline trail_step charged-holdout scan for the live 3 (measure-only).

Uses on-disk ``data/holdout_bars`` + ``scripts.trail_exec.propose_trail_upgrade``.
Never POSTs. Writes ``.bridge/TRAIL_MFE_BOOK_SCAN.json``.

    python scripts/trail_mfe_book_scan.py
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.panel_session import opener as _panel_opener  # noqa: E402
from scripts.trail_exec import (  # noqa: E402
    TRAIL_STEP_CANDIDATES,
    _score_steps,
    best_trail_upgrade,
)

PANEL = "http://127.0.0.1:8900"
LIVE = ("GER40", "NAS100", "XAUUSD")
OUT = ROOT / ".bridge" / "TRAIL_MFE_BOOK_SCAN.json"


def fetch_symbol_rows(panel: str = PANEL) -> list[dict[str, Any]]:
    op = _panel_opener(panel)
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/symbols", headers={"Origin": panel},
            ),
            timeout=20,
        ).read().decode()
    )
    rows = body.get("symbols") if isinstance(body, dict) else None
    return list(rows) if isinstance(rows, list) else []


def scan_row(row: dict[str, Any]) -> dict[str, Any]:
    sym = str(row.get("symbol") or "")
    try:
        live_step = float(row.get("trail_step_atr") or 0.0)
        live_sl = float(row.get("sl_atr_mult") or 0.0)
    except (TypeError, ValueError):
        live_step = 0.0
        live_sl = 0.0
    steps = tuple(sorted(set(TRAIL_STEP_CANDIDATES) | {live_step}))
    scored = _score_steps(row, steps)
    live_hold = None
    for step, hold in scored.items():
        if abs(float(step) - live_step) < 1e-9 and isinstance(hold, dict):
            live_hold = hold
            break
    pick = best_trail_upgrade(live_step, scored) if live_step > 0 else None
    compact = {
        str(k): (
            {
                "net_r": (v or {}).get("net_r"),
                "profit_factor": (v or {}).get("profit_factor"),
                "trades": (v or {}).get("trades"),
                "capture": (v or {}).get("capture"),
            }
            if isinstance(v, dict) else None
        )
        for k, v in sorted(scored.items(), key=lambda kv: float(kv[0]))
    }
    return {
        "symbol": sym,
        "strategy": row.get("strategy"),
        "timeframe": row.get("timeframe"),
        "sl_atr_mult": live_sl,
        "trail_step_atr": live_step,
        "trail_start_atr": row.get("trail_start_atr"),
        "r_for_trail_green": (
            round(live_step / live_sl, 3) if live_sl > 0 else None
        ),
        "live_holdout": live_hold,
        "propose": pick,
        "verdict": "APPLY_CANDIDATE" if pick else "KEEP",
        "scored": compact,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--panel", default=PANEL)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument(
        "--symbols",
        default=",".join(LIVE),
        help="Comma list of live symbols to scan",
    )
    args = ap.parse_args(argv)
    want = {s.strip() for s in args.symbols.split(",") if s.strip()}

    rows = [r for r in fetch_symbol_rows(args.panel) if r.get("symbol") in want]
    report: dict[str, Any] = {
        "at": datetime.now(UTC).isoformat(),
        "note": "measure-only; no POST",
        "rows": [],
    }
    for row in rows:
        print(f"scan {row.get('symbol')} {row.get('timeframe')} ...", flush=True)
        report["rows"].append(scan_row(row))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for r in report["rows"]:
        prop = r.get("propose")
        delta = None
        if prop:
            try:
                delta = float(prop.get("net_r") or 0) - float(prop.get("live_net_r") or 0)
            except (TypeError, ValueError):
                delta = None
        print(
            f"{r['symbol']}: {r['verdict']} live_step={r['trail_step_atr']} "
            f"green_R={r.get('r_for_trail_green')} "
            f"propose={prop.get('trail_step_atr') if prop else None} "
            f"dR={delta}",
            flush=True,
        )
    print(f"wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
