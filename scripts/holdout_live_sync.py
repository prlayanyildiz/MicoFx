"""Holdout vs live gap audit and auto-align (flat symbols only)."""
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spread_exec import apply_spread_widen  # noqa: E402

FAM = frozenset({"burst", "mtf_pullback", "ichimoku", "channel_break"})
DB_PATH = ROOT / "data" / "micofx.db"
PANEL = "http://127.0.0.1:8900"

# Dominant spread blocks + low fill -> execution gap (not strategy drift)
_EXEC_SPREAD_MIN = 10
_EXEC_FILL_MAX = 0.30
# Best validated opt must beat live holdout stamp by this much to auto-apply
_HOLDOUT_GAP_R = 8.0


def _get(path: str, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(f"{PANEL}{path}", headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _post(path: str, headers: dict[str, str], body: dict[str, Any] | None = None) -> tuple[bool, Any]:
    data = json.dumps(body or {}).encode()
    h = {**headers, "Origin": PANEL, "Content-Type": "application/json"}
    req = urllib.request.Request(f"{PANEL}{path}", data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return True, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return False, json.loads(raw)
        except json.JSONDecodeError:
            return False, raw


def _aggregate_entry_blocks(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        sym = str(row.get("symbol") or "")
        if not sym:
            continue
        agg = out.setdefault(sym, {"signals": 0, "opened": 0, "spread": 0})
        agg["signals"] += int(row.get("signals") or 0)
        agg["opened"] += int(row.get("opened") or 0)
        agg["spread"] += int((row.get("blocks") or {}).get("spread") or 0)
    return out


def _best_validated_run(headers: dict[str, str], symbol: str) -> dict[str, Any] | None:
    hist = _get(f"/api/opt/history?symbol={symbol}&limit=50", headers)
    best: dict[str, Any] | None = None
    best_h = -1e9
    for row in hist.get("history") or []:
        if row.get("strategy") not in FAM or not row.get("validated"):
            continue
        h = float((row.get("holdout") or {}).get("net_r") or 0)
        if h > best_h:
            best_h = h
            best = row
    return best


def sync_flat_symbols(headers: dict[str, str]) -> list[str]:
    """Close holdout/live gaps on flat symbols. Returns log lines."""
    done: list[str] = []
    st = _get("/api/state", headers)
    if (st.get("opt") or {}).get("busy"):
        return ["holdout_live: opt busy — atlandi"]

    open_syms = {str(p.get("symbol") or "") for p in st.get("positions") or []}
    eb = _aggregate_entry_blocks(list(_get("/api/analysis/entry-blocks", headers).get("rows") or []))
    ai_rows = {r["symbol"]: r for r in (st.get("ai") or {}).get("symbols") or []}

    db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    for row in db.execute("SELECT symbol, payload FROM symbols ORDER BY symbol"):
        sym = row[0]
        payload = json.loads(row[1])
        if not payload.get("enabled") or sym in open_syms:
            continue
        hold_r = float(((payload.get("opt_summary") or {}).get("holdout") or {}).get("net_r") or 0)
        eb_r = eb.get(sym, {})
        sig = int(eb_r.get("signals") or 0)
        fill = float(eb_r.get("opened") or 0) / sig if sig else 0.0
        spread_n = int(eb_r.get("spread") or 0)
        ai = ai_rows.get(sym) or {}
        live_pf = float(ai.get("profit_factor") or 0)
        live_n = int(ai.get("trades") or 0)

        exec_gap = fill < _EXEC_FILL_MAX and spread_n >= _EXEC_SPREAD_MIN
        drift = live_n >= 15 and live_pf < 0.95 and hold_r >= 25

        if exec_gap:
            cap = float(payload.get("max_spread_atr") or 0.0)
            hist = _get(f"/api/opt/history?symbol={sym}&limit=50", headers)
            ok, msg = apply_spread_widen(
                headers, panel=PANEL, symbol=sym, current_cap=cap,
                history=list(hist.get("history") or []))
            done.append(msg if ok else f"FAIL {msg}")

        best = _best_validated_run(headers, sym)
        if best is None:
            continue
        best_h = float((best.get("holdout") or {}).get("net_r") or 0)
        if best_h <= hold_r + _HOLDOUT_GAP_R:
            continue
        if drift or best_h > hold_r + _HOLDOUT_GAP_R * 2:
            ok, body = _post("/api/opt/apply", headers, {
                "symbol": sym, "run_id": int(best["id"]), "force": True,
            })
            if ok:
                done.append(
                    f"{sym} holdout hizala run {best['id']} "
                    f"{best.get('strategy')}/{best.get('timeframe')} "
                    f"{hold_r:+.0f}R->{best_h:+.0f}R")
            else:
                detail = body.get("detail", body) if isinstance(body, dict) else body
                done.append(f"{sym} apply fail: {str(detail)[:80]}")
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
