"""Leverage-aware kasa auto-tune — sizes the book from equity + broker leverage."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

PANEL = "http://127.0.0.1:8900"


def compute_kasa_targets(
    *,
    equity: float,
    leverage: float,
    n_enabled: int,
    global_free_slots: int,
    margin_usage_pct: float,
    max_margin_usage_pct: float,
    lot_multiplier: float,
    max_concurrent_risk_pct: float,
    zero_lot: int = 0,
    lot_blocks: int = 0,
) -> dict[str, Any]:
    """Return recommended system knobs and human-readable reasons."""
    eq = max(0.0, float(equity or 0.0))
    lev = max(1.0, float(leverage or 1.0))
    n = max(1, int(n_enabled or 1))
    lot_cur = float(lot_multiplier or 1.0)

    if lev >= 400:
        margin_target = min(85.0, 55.0 + eq / 40.0 + n * 2.0)
    elif lev >= 100:
        margin_target = min(80.0, 50.0 + eq / 60.0 + n * 1.5)
    else:
        margin_target = min(75.0, 45.0 + eq / 80.0)
    margin_target = round(max(55.0, min(85.0, margin_target)), 1)

    if eq < 120:
        lot_target = 0.65
    elif eq < 250:
        lot_target = 0.85
    elif eq < 500:
        lot_target = 1.0
    elif eq < 1200:
        lot_target = 1.15
    elif eq < 3000:
        lot_target = 1.3
    else:
        lot_target = min(1.6, 1.3 + (eq - 3000) / 8000.0)
    lot_target = round(lot_target, 2)

    conc_target = round(min(50.0, 25.0 + n * 4.0 + (5.0 if lev >= 200 else 0.0)), 1)

    if global_free_slots == 0 and margin_usage_pct >= max_margin_usage_pct * 0.9:
        lot_target = round(max(0.5, lot_cur * 0.85), 2)

    heal_notes: list[str] = []
    if zero_lot > 0:
        margin_target = round(min(85.0, margin_target + 5.0 + zero_lot * 2.0), 1)
        lot_target = round(min(1.2, lot_target + 0.05 * zero_lot), 2)
        heal_notes.append(f"lot=0 sembol {zero_lot} -> marj/lot artir")

    patch: dict[str, Any] = {}
    reasons: list[str] = list(heal_notes)

    if abs(margin_target - float(max_margin_usage_pct or 0)) >= 1.0:
        patch["max_margin_usage_pct"] = margin_target
        reasons.append(
            f"marj %{max_margin_usage_pct:g}->%{margin_target:g} (1:{int(lev)} x {n} sembol)")

    if abs(lot_target - lot_cur) >= 0.05:
        patch["lot_multiplier"] = lot_target
        reasons.append(f"lot_mult {lot_cur}->{lot_target} (eq ${eq:.0f})")

    if abs(conc_target - float(max_concurrent_risk_pct or 0)) >= 2.0:
        patch["max_concurrent_risk_pct"] = conc_target
        reasons.append(f"conc_risk %{max_concurrent_risk_pct:g}->%{conc_target:g}")

    return {
        "patch": patch,
        "targets": {
            "max_margin_usage_pct": margin_target,
            "lot_multiplier": lot_target,
            "max_concurrent_risk_pct": conc_target,
        },
        "reasons": reasons,
        "equity": eq,
        "leverage": lev,
        "n_enabled": n,
        "global_free_slots": global_free_slots,
        "margin_usage_pct": margin_usage_pct,
    }


def apply_kasa_tune(headers: dict[str, str]) -> list[str]:
    """Fetch live state and POST system patch when targets diverge."""
    try:
        req = urllib.request.Request(f"{PANEL}/api/state", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            st = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return ["kasa_auto: state okunamadi"]

    acc = st.get("account") or {}
    cap = st.get("capacity") or {}
    sys = st.get("system") or {}
    rows = [r for r in (cap.get("rows") or []) if r.get("enabled")]
    zero_lot = sum(1 for r in rows if float(r.get("lot") or 0) <= 0)

    lot_blocks = 0
    try:
        req = urllib.request.Request(
            f"{PANEL}/api/analysis/entry-blocks", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            eb = json.loads(resp.read().decode())
        for row in eb.get("rows") or []:
            if not row.get("symbol"):
                continue
            lot_blocks += int((row.get("blocks") or {}).get("lot") or 0)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        pass

    plan = compute_kasa_targets(
        equity=float(acc.get("equity") or 0),
        leverage=float(acc.get("leverage") or 1),
        n_enabled=len(rows),
        global_free_slots=int(cap.get("global_free_slots") or 0),
        margin_usage_pct=float(cap.get("margin_usage_pct") or 0),
        max_margin_usage_pct=float(
            sys.get("max_margin_usage_pct") or cap.get("max_margin_usage_pct") or 85),
        lot_multiplier=float(sys.get("lot_multiplier") or cap.get("lot_multiplier") or 1),
        max_concurrent_risk_pct=float(
            sys.get("max_concurrent_risk_pct") or cap.get("max_concurrent_risk_pct") or 50),
        zero_lot=zero_lot,
        lot_blocks=lot_blocks,
    )

    done: list[str] = [
        f"KASA eq ${plan['equity']:.0f} lev 1:{int(plan['leverage'])} "
        f"{plan['n_enabled']} sembol slot {plan['global_free_slots']} "
        f"hedef lotx{plan['targets']['lot_multiplier']} "
        f"marj %{plan['targets']['max_margin_usage_pct']:g}",
    ]
    if zero_lot:
        done.append(f"UYARI {zero_lot} sembol lot=0")

    patch = dict(plan["patch"])
    if not sys.get("autostart_bot"):
        patch["autostart_bot"] = True
        plan["reasons"].append("autostart_bot ac")

    if not patch:
        done.append("kasa_auto: ayarlar uygun")
        return done

    data = json.dumps(patch).encode()
    h = {**headers, "Origin": PANEL, "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(f"{PANEL}/api/system", data=data, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            json.loads(resp.read().decode())
        for r in plan["reasons"]:
            done.append(f"kasa {r}")
    except urllib.error.HTTPError as exc:
        done.append(f"kasa_auto fail: {exc.read().decode()[:120]}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        done.append(f"kasa_auto fail: {exc}")
    return done
