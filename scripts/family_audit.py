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
    """DISABLED auto-apply — paper holdout family swaps crushed measured books.

    04.09 income --auto: SpotBrent mtf→burst (msa 0.05→0.18), NAS burst→mtf.
    Keep as an explicit operator tool only; ``income_dev_loop --auto`` must
    call ``audit_report`` instead.
    """
    del headers, min_gap_r
    return ["family: auto-hizala KAPALI (audit-only; 04.09 SpotBrent/NAS)"]


def main() -> int:
    h = session()
    for line in audit_report(h):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
