"""Leverage-driven kasa auto-tune — HTTP wrapper around micofx.kasa_sizing."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from micofx.kasa_sizing import compute_kasa_targets

PANEL = "http://127.0.0.1:8900"

# Re-export for tests that import from scripts.kasa_auto
__all__ = ["compute_kasa_targets", "apply_kasa_tune"]


def apply_kasa_tune(headers: dict[str, str]) -> list[str]:
    """Fetch live state and POST margin patch when targets diverge.

    Lot / concurrent are sized inline in ``RiskManager``; this path only
    keeps ``max_margin_usage_pct`` (and autostart) in range.
    """
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

    broker_lev = float(acc.get("leverage") or 1)
    try:
        want = float(sys.get("target_leverage") or 0)
    except (TypeError, ValueError):
        want = 0.0
    eff = broker_lev if want <= 0 else min(want, broker_lev)

    plan = compute_kasa_targets(
        equity=float(acc.get("equity") or 0),
        leverage=eff,
        n_enabled=max(1, len(rows)),
        global_free_slots=int(cap.get("global_free_slots") or 0),
        margin_usage_pct=float(cap.get("margin_usage_pct") or 0),
        max_margin_usage_pct=float(
            sys.get("max_margin_usage_pct") or cap.get("max_margin_usage_pct") or 85),
        lot_multiplier=float(sys.get("lot_multiplier") or cap.get("lot_multiplier") or 1),
        max_concurrent_risk_pct=float(
            sys.get("max_concurrent_risk_pct") or cap.get("max_concurrent_risk_pct") or 50),
        zero_lot=zero_lot,
        broker_leverage=broker_lev,
    )

    done: list[str] = [
        f"KASA eq ${plan['equity']:.0f} lev 1:{int(plan['leverage'])} "
        f"(broker 1:{int(plan['broker_leverage'])}) "
        f"inline lotx{plan['targets']['lot_multiplier']} "
        f"conc %{plan['targets']['max_concurrent_risk_pct']:g} "
        f"marj %{plan['targets']['max_margin_usage_pct']:g}",
    ]
    if zero_lot:
        done.append(f"UYARI {zero_lot} sembol lot=0")

    # Lot/concurrent are inline — only margin (and autostart) may patch here.
    patch: dict[str, Any] = {}
    if "max_margin_usage_pct" in plan["patch"]:
        patch["max_margin_usage_pct"] = plan["patch"]["max_margin_usage_pct"]
    if not sys.get("autostart_bot"):
        patch["autostart_bot"] = True
        plan["reasons"].append("autostart_bot ac")

    if not patch:
        done.append("kasa_auto: marj uygun (lot/conc inline)")
        return done

    data = json.dumps(patch).encode()
    h = {**headers, "Origin": PANEL, "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(f"{PANEL}/api/system", data=data, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            json.loads(resp.read().decode())
        for r in plan["reasons"]:
            if "lot_mult" in str(r) or "conc_risk" in str(r):
                continue
            done.append(f"kasa {r}")
    except urllib.error.HTTPError as exc:
        done.append(f"kasa_auto fail: {exc.read().decode()[:120]}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        done.append(f"kasa_auto fail: {exc}")
    return done
