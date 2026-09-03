"""Family/holdout audit and safe auto-align for enabled symbols."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
FAM = frozenset({"burst", "mtf_pullback", "channel_break"})


def session() -> dict[str, str]:
    req = urllib.request.Request(f"{PANEL}/", method="GET")
    resp = urllib.request.urlopen(req, timeout=10)
    cookies = resp.headers.get_all("Set-Cookie") or []
    h = {"Origin": PANEL}
    if cookies:
        h["Cookie"] = "; ".join(x.split(";")[0] for x in cookies)
    return h


def _get(path: str, h: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(f"{PANEL}{path}", headers=h, method="GET")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def audit_report(headers: dict[str, str]) -> list[str]:
    """Human-readable family audit lines."""
    lines: list[str] = []
    syms = _get("/api/symbols", headers).get("symbols") or []
    for row in syms:
        if not row.get("enabled"):
            continue
        sym = row["symbol"]
        live = f"{row.get('strategy')}/{row.get('timeframe')}"
        hold_r = float(((row.get("opt_summary") or {}).get("holdout") or {}).get("net_r") or 0)
        hist = _get(f"/api/opt/history?symbol={sym}&limit=40", headers)
        val = [r for r in hist.get("history") or [] if r.get("validated") and r.get("strategy") in FAM]
        val.sort(key=lambda r: float((r.get("holdout") or {}).get("net_r") or 0), reverse=True)
        best = val[0] if val else None
        if best and best.get("strategy") == row.get("strategy") and best.get("timeframe") == row.get("timeframe"):
            lines.append(f"{sym} aile OK {live} hold={hold_r:+.0f}R")
        elif best:
            bh = float((best.get("holdout") or {}).get("net_r") or 0)
            lines.append(
                f"{sym} aile GAP live={live} ({hold_r:+.0f}R) "
                f"best={best.get('strategy')}/{best.get('timeframe')} ({bh:+.0f}R)")
        else:
            lines.append(f"{sym} aile: validated run yok")
    return lines


def sync_family_gaps(headers: dict[str, str], *, min_gap_r: float = 15.0) -> list[str]:
    """Apply best validated family/TF when live holdout lags by min_gap_r (flat only)."""
    done: list[str] = []
    st = _get("/api/state", headers)
    if (st.get("opt") or {}).get("busy"):
        return ["family: opt busy — atlandi"]
    open_syms = {str(p.get("symbol") or "") for p in st.get("positions") or []}

    for row in _get("/api/symbols", headers).get("symbols") or []:
        if not row.get("enabled") or row["symbol"] in open_syms:
            continue
        sym = row["symbol"]
        hold_r = float(((row.get("opt_summary") or {}).get("holdout") or {}).get("net_r") or 0)
        hist = _get(f"/api/opt/history?symbol={sym}&limit=40", headers)
        val = [r for r in hist.get("history") or [] if r.get("validated") and r.get("strategy") in FAM]
        if not val:
            continue
        val.sort(key=lambda r: float((r.get("holdout") or {}).get("net_r") or 0), reverse=True)
        best = val[0]
        if best.get("strategy") == row.get("strategy") and best.get("timeframe") == row.get("timeframe"):
            done.append(f"{sym} aile OK {row.get('strategy')}/{row.get('timeframe')} hold={hold_r:+.0f}R")
            continue
        best_h = float((best.get("holdout") or {}).get("net_r") or 0)
        if best_h < hold_r + min_gap_r:
            continue
        payload = json.dumps({"symbol": sym, "run_id": int(best["id"]), "force": True}).encode()
        h = {**headers, "Origin": PANEL, "Content-Type": "application/json"}
        req = urllib.request.Request(f"{PANEL}/api/opt/apply", data=payload, headers=h, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                json.loads(resp.read().decode())
            done.append(
                f"{sym} aile hizala run {best['id']} "
                f"{best.get('strategy')}/{best.get('timeframe')} "
                f"{hold_r:+.0f}R->{best_h:+.0f}R")
        except urllib.error.HTTPError as exc:
            done.append(f"{sym} aile apply fail: {exc.read().decode()[:80]}")
    return done


def main() -> int:
    h = session()
    for line in audit_report(h):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
