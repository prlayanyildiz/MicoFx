"""One-shot dry-run: NAS100 live session vs SEARCH challengers. No live write."""
from __future__ import annotations

import http.cookiejar
import json
import urllib.request
from copy import deepcopy
from pathlib import Path

from scripts.exec_gates import charged_slice_nets, charged_slice_report, upgrade_robust
from scripts.session_exec import _score_windows, best_session_upgrade, live_trade_sessions

PANEL = "http://127.0.0.1:8900"
OUT = Path(".bridge/NAS100_SESSION_REEVAL_ONCE.json")


def main() -> int:
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(PANEL + "/")
    raw = json.loads(
        op.open(
            urllib.request.Request(PANEL + "/api/symbols", headers={"Origin": PANEL})
        ).read().decode()
    )
    rows = raw if isinstance(raw, list) else (raw.get("symbols") or [])
    nas = next(r for r in rows if str(r.get("symbol")) == "NAS100")
    live = live_trade_sessions(nas)
    cands = [
        [{"start": "15:00", "end": "21:00"}],
        [{"start": "14:00", "end": "22:00"}],
        [{"start": "14:00", "end": "21:00"}],
        [{"start": "01:00", "end": "23:59"}],
    ]
    scored = _score_windows(nas, cands)
    scored_out = []
    for w, h in scored:
        label = f"{w[0]['start']}-{w[0]['end']}"
        if not isinstance(h, dict):
            scored_out.append({"win": label, "hold": None})
            continue
        scored_out.append({
            "win": label,
            "net_r": round(float(h.get("net_r") or 0), 2),
            "pf": round(float(h.get("profit_factor") or 0), 3),
            "trades": h.get("trades"),
            "max_dd_r": round(float(h.get("max_dd_r") or 0), 2),
        })
    pick = best_session_upgrade(live, scored)
    chal = deepcopy(nas)
    chal["sessions"] = [{"start": "14:00", "end": "22:00"}]
    chal["use_sessions"] = True
    live_rep = charged_slice_report(nas)
    chal_rep = charged_slice_report(chal)
    robust = upgrade_robust(charged_slice_nets(nas), charged_slice_nets(chal))
    prev = {}
    if OUT.is_file():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    report = {
        **prev,
        "dry_run_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "status": "dry_run_measured_await_unfreeze",
        "do_not_run_now": True,
        "when": "after 25/25 baseline AND exec unfreeze decision",
        "live": {
            "sessions": live,
            "use_sessions": nas.get("use_sessions"),
            "strategy": nas.get("strategy"),
            "timeframe": nas.get("timeframe"),
        },
        "scored": scored_out,
        "best_session_upgrade": pick,
        "chal_14_22": {
            "upgrade_robust_vs_live": robust,
            "live_slice": {
                "wins_valid": (live_rep or {}).get("wins_valid"),
                "valid_n": (live_rep or {}).get("valid_n"),
                "nets": (live_rep or {}).get("nets"),
            },
            "chal_slice": {
                "wins_valid": (chal_rep or {}).get("wins_valid"),
                "valid_n": (chal_rep or {}).get("valid_n"),
                "nets": (chal_rep or {}).get("nets"),
            },
        },
        "note": "Measurement only — no POST. Apply via reevaluate_sessions / session_exec after unfreeze.",
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "scored": scored_out,
        "pick": pick,
        "upgrade_robust_14_22": robust,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
