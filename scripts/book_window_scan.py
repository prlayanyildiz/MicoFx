"""Book-wide field scan via window_reconcile — report only, no apply."""
from __future__ import annotations

import http.cookiejar
import json
import urllib.request
from datetime import datetime
from pathlib import Path

from scripts.window_reconcile import field_window_compare

PANEL = "http://127.0.0.1:8900"
OUT = Path(".bridge/WINDOW_RECONCILE_BOOK_SCAN.json")

# field -> challenger list (skip live value in compare loop)
SCANS = {
    "min_body_ratio": [0.0, 0.1, 0.2, 0.3],
    "pull_depth_atr": [0.5, 0.8, 1.2, 1.6],
    "trail_step_atr": [0.4, 0.6, 0.8, 1.2, 1.6, 2.2, 2.8],
    "adx_min": [0.0, 12.0, 18.0, 25.0],
    "atr_pct_min": [0.0, 0.1, 0.2, 0.25],
    "sl_atr_mult": None,  # filled from nearby live ± grid later if needed
}


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
        return [r for r in raw if isinstance(r, dict) and r.get("enabled")]
    return [
        r for r in (raw.get("symbols") or raw.get("rows") or [])
        if isinstance(r, dict) and r.get("enabled")
    ]


def main() -> int:
    rows = _symbols()
    hits = []
    keep_conflict = []
    hold_only = []
    for row in rows:
        sym = str(row.get("symbol") or "")
        fam = str(row.get("strategy") or "")
        for field, cands in SCANS.items():
            if cands is None:
                continue
            if field == "pull_depth_atr" and fam != "mtf_pullback":
                continue
            live = float(row.get(field) or 0.0)
            for v in cands:
                if abs(v - live) < 1e-12:
                    continue
                rep = field_window_compare(row, field=field, challenger=v)
                dec = rep.get("decision")
                item = {
                    "symbol": sym,
                    "field": field,
                    "live": live,
                    "challenger": v,
                    "decision": dec,
                    "slice": rep.get("slice"),
                    "holdout": rep.get("holdout_last_seg"),
                }
                if dec == "APPLY":
                    hits.append(item)
                elif dec == "KEEP_CONFLICT_frontload":
                    keep_conflict.append(item)
                elif dec == "HOLD_ONLY_review":
                    hold_only.append(item)
    report = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "apply_hits": hits,
        "frontload_conflicts": keep_conflict,
        "hold_only_review": hold_only,
        "note": "FROZEN — queue only. APPLY needs holdout+slice.",
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "apply_n": len(hits),
        "conflict_n": len(keep_conflict),
        "hold_only_n": len(hold_only),
        "apply_hits": hits,
        "conflicts_preview": keep_conflict[:8],
        "hold_only_preview": hold_only[:8],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
