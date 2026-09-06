"""Holdout vs live gap audit — spread recovery on flat symbols only."""
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from micofx.entry_pressure import spread_pressure  # noqa: E402
from scripts.spread_exec import apply_spread_widen  # noqa: E402

DB_PATH = ROOT / "data" / "micofx.db"
PANEL = "http://127.0.0.1:8900"

# Dominant spread blocks + low fill -> execution gap (not strategy drift)
_EXEC_SPREAD_MIN = 10
_EXEC_FILL_MAX = 0.30


def _get(path: str, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(f"{PANEL}{path}", headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _aggregate_entry_blocks(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        sym = str(row.get("symbol") or "")
        if not sym:
            continue
        agg = out.setdefault(sym, {"signals": 0, "opened": 0, "spread": 0})
        agg["signals"] += int(row.get("signals") or 0)
        agg["opened"] += int(row.get("opened") or 0)
        # Keep the row's retries so spread_pressure can see them after merge.
        prev = int(agg.get("spread") or 0)
        pressure = spread_pressure(row)
        agg["spread"] = max(prev, pressure)
        # Stash last retries for pressure on the merged dict shape.
        retries = dict(agg.get("retries") or {})
        row_retries = row.get("retries") or {}
        if isinstance(row_retries, dict):
            for k, v in row_retries.items():
                try:
                    retries[k] = int(retries.get(k) or 0) + int(v or 0)
                except (TypeError, ValueError):
                    continue
        agg["retries"] = retries
        blocks = dict(agg.get("blocks") or {})
        row_blocks = row.get("blocks") or {}
        if isinstance(row_blocks, dict):
            for k, v in row_blocks.items():
                try:
                    blocks[k] = int(blocks.get(k) or 0) + int(v or 0)
                except (TypeError, ValueError):
                    continue
        agg["blocks"] = blocks
    return out


def sync_flat_symbols(headers: dict[str, str]) -> list[str]:
    """Spread-only recovery on flat enabled symbols. Returns log lines."""
    done: list[str] = []
    st = _get("/api/state", headers)
    if (st.get("opt") or {}).get("busy"):
        return ["holdout_live: opt busy — atlandi"]
    if not (st.get("system") or {}).get("charge_costs", True):
        return ["holdout_live: charge_costs=false — spread sync atlandi"]

    open_syms = {str(p.get("symbol") or "") for p in st.get("positions") or []}
    eb = _aggregate_entry_blocks(list(_get("/api/analysis/entry-blocks", headers).get("rows") or []))

    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    for row in db.execute("SELECT symbol, payload FROM symbols ORDER BY symbol"):
        sym = row[0]
        payload = json.loads(row[1])
        if not payload.get("enabled") or sym in open_syms:
            continue
        eb_r = eb.get(sym, {})
        sig = int(eb_r.get("signals") or 0)
        fill = float(eb_r.get("opened") or 0) / sig if sig else 0.0
        spread_n = int(eb_r.get("spread") or 0)
        if spread_n < _EXEC_SPREAD_MIN:
            spread_n = spread_pressure(eb_r)

        exec_gap = fill < _EXEC_FILL_MAX and spread_n >= _EXEC_SPREAD_MIN
        if not exec_gap:
            continue
        cap = float(payload.get("max_spread_atr") or 0.0)
        hist = _get(f"/api/opt/history?symbol={sym}&limit=50", headers)
        ok, msg = apply_spread_widen(
            headers, panel=PANEL, symbol=sym, current_cap=cap,
            history=list(hist.get("history") or []),
            strategy=str(payload.get("strategy") or "") or None)
        done.append(msg if ok else f"FAIL {msg}")
    db.close()
    return done


def main() -> int:
    req = urllib.request.Request(f"{PANEL}/", method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        cookies = resp.headers.get_all("Set-Cookie") or []
    headers = {
        "Origin": PANEL,
        "Cookie": "; ".join(c.split(";")[0] for c in cookies) if cookies else "",
    }
    lines = sync_flat_symbols(headers)
    if not lines:
        print("holdout_live: hizali (flat)")
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
