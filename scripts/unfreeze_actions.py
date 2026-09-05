"""Unfreeze action plan — status now; execute only when gates clear.

Does not lift EXEC_PIPELINE_FROZEN. Default is plan-only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / ".bridge"

from scripts.exec_gates import pipeline_frozen  # noqa: E402
from scripts.income_dev_loop import (  # noqa: E402
    load_action_queues,
    load_day25_checklist,
)


def readiness() -> dict[str, Any]:
    frozen = bool(pipeline_frozen())
    bl: dict[str, Any] = {}
    try:
        from scripts.xau_streak_watch import baseline_status, fetch_autopsy_rows
        rows = fetch_autopsy_rows("http://127.0.0.1:8900")
        bl = baseline_status(len(rows))
    except Exception as exc:
        bl = {"error": str(exc)}
    n = int(bl.get("new_trades") or 0)
    target = int(bl.get("target") or 25)
    ready = (not frozen) and n >= target
    return {
        "frozen": frozen,
        "baseline_new": n,
        "baseline_target": target,
        "ready_to_execute": ready,
        "baseline": bl,
    }


def plan() -> dict[str, Any]:
    ready = readiness()
    actions = load_action_queues(BRIDGE)
    ordered = []
    for a in actions:
        path = str(a.get("_path") or "")
        if path.startswith("XAU_MIN_BODY"):
            st = str(a.get("status") or "")
            if "RESOLVED_KEEP" in st or "CONFLICT" in st:
                auto = False
                intent = (
                    "KEEP live min_body (resolved — recent edge wins)"
                    if "RESOLVED" in st else
                    "CONFLICT holdout vs slices — KEEP until reconciled"
                )
            else:
                auto = bool(st.startswith("measured_ready"))
                intent = (
                    "APPLY min_body_ratio via body_exec (queued challenger)"
                    if auto else "review XAU min_body queue"
                )
        elif path.startswith("NAS100_MIN_BODY"):
            st = str(a.get("status") or "")
            if "BLOCKED" in st:
                auto = False
                intent = "KEEP NAS100 min_body (neighbor gap blocked)"
            else:
                auto = st.startswith("measured_ready")
                intent = (
                    "APPLY NAS100 min_body via body_exec"
                    if auto else "review NAS100 min_body"
                )
        elif path.startswith("NAS100_SESSION"):
            intent = "KEEP live session (do not widen) — reconfirm only"
            auto = False
        elif path.startswith("WFO_APPLY"):
            intent = "Wire anchored_wfo_apply_ok into upgrade_robust (code)"
            auto = False
        elif path.startswith("XAU_TRAIL_STEP_GIVEBACK"):
            intent = (
                "KEEP XAU trail_step 2.5 (AXIS_CLOSED — geometry OPTIMUM; "
                "trail mech HEALTHY closed-bar; no apply)"
            )
            auto = False
        elif path.startswith("XAU_BE_AT_R"):
            intent = (
                "KEEP XAU breakeven_at_r 1.5 (HOLD_ONLY — holdout likes "
                "1.2/1.0, slice+robust fail; no auto)"
            )
            auto = False
        elif path.startswith("GER40_TRAIL"):
            intent = "KEEP GER40 trail_step (HOLD_ONLY — slice fails robust)"
            auto = False
        elif path.startswith("GER40"):
            intent = "Optional MT5 recapture (LOW) — trim already done"
            auto = False
        else:
            intent = "review"
            auto = False
        ordered.append({**a, "intent": intent, "auto_on_unfreeze": auto})
    d25 = load_day25_checklist(BRIDGE)
    return {
        "readiness": ready,
        "day25_checklist": d25,
        "actions": ordered,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true",
                   help="Run auto actions only if frozen=False and baseline>=25")
    args = p.parse_args()
    rep = plan()
    if args.execute:
        if not rep["readiness"].get("ready_to_execute"):
            rep["execute"] = {
                "ok": False,
                "reason": "not ready (need unfrozen + baseline>=target)",
            }
        else:
            # Only board rows with auto_on_unfreeze=True. RESOLVED_KEEP /
            # BLOCKED / HOLD_ONLY must never re-enter body_exec (Claude 01:14
            # shakeout remeasure: XAU 0.1 OOS flipped; live 0.3 stays).
            auto_rows = [
                a for a in (rep.get("actions") or [])
                if a.get("auto_on_unfreeze")
            ]
            if not auto_rows:
                rep["execute"] = {
                    "ok": True,
                    "skipped": "no auto_on_unfreeze actions",
                }
            else:
                try:
                    import http.cookiejar
                    import urllib.request

                    from scripts.body_exec import apply_body_upgrade

                    panel = "http://127.0.0.1:8900"
                    cj = http.cookiejar.CookieJar()
                    op = urllib.request.build_opener(
                        urllib.request.HTTPCookieProcessor(cj))
                    op.open(panel + "/")
                    raw = json.loads(
                        op.open(
                            urllib.request.Request(
                                panel + "/api/symbols",
                                headers={"Origin": panel},
                            )
                        ).read().decode()
                    )
                    rows = raw if isinstance(raw, list) else (
                        raw.get("symbols") or raw.get("rows") or [])
                    results = []
                    for act in auto_rows:
                        path = str(act.get("_path") or "")
                        if not path.startswith("XAU_MIN_BODY"):
                            results.append({
                                "path": path,
                                "ok": False,
                                "reason": "auto executor only handles XAU body",
                            })
                            continue
                        xau = next(
                            r for r in rows
                            if isinstance(r, dict)
                            and r.get("symbol") == "XAUUSD"
                        )
                        ok, msg = apply_body_upgrade(
                            {"Origin": panel}, panel=panel, row=xau)
                        results.append({"path": path, "ok": ok, "body": msg})
                    rep["execute"] = {
                        "ok": all(r.get("ok") for r in results),
                        "results": results,
                    }
                except Exception as exc:
                    rep["execute"] = {"ok": False, "reason": str(exc)}
    print(json.dumps(rep, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
