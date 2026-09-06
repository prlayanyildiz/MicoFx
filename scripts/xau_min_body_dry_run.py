"""XAUUSD min_body_ratio dry-run (Claude EK23 survivor). No live write."""
from __future__ import annotations

import http.cookiejar
import json
import urllib.request
from datetime import datetime
from pathlib import Path

from scripts.window_reconcile import field_window_compare

PANEL = "http://127.0.0.1:8900"
OUT = Path(".bridge/XAU_MIN_BODY_DRY_RUN.json")
CANDIDATES = [0.0, 0.1, 0.2, 0.3]


def _symbols() -> list[dict]:
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(PANEL + "/")
    raw = json.loads(
        op.open(
            urllib.request.Request(PANEL + "/api/symbols", headers={"Origin": PANEL})
        ).read().decode()
    )
    if isinstance(raw, list):
        return raw
    return list(raw.get("symbols") or raw.get("rows") or [])


def main() -> int:
    rows = _symbols()
    xau = next(r for r in rows if isinstance(r, dict) and r.get("symbol") == "XAUUSD")
    live_v = float(xau.get("min_body_ratio") or 0.0)
    scored = []
    for v in CANDIDATES:
        if abs(v - live_v) < 1e-12:
            continue
        scored.append(field_window_compare(xau, field="min_body_ratio", challenger=v))
    report = {
        "dry_run_at": datetime.now().isoformat(timespec="seconds"),
        "status": "reconcile_both_windows",
        "do_not_apply_now": True,
        "live": live_v,
        "strategy": xau.get("strategy"),
        "timeframe": xau.get("timeframe"),
        "scored": scored,
        "note": "APPLY only if decision==APPLY (holdout AND slice). FROZEN.",
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
