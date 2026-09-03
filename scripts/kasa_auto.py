"""Margin%-driven kasa auto-tune — HTTP wrapper around micofx.kasa_sizing."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from micofx.kasa_sizing import compute_kasa_targets

PANEL = "http://127.0.0.1:8900"

__all__ = ["compute_kasa_targets", "apply_kasa_tune"]


def apply_kasa_tune(headers: dict[str, str]) -> list[str]:
    """Log inline targets; do not PATCH margin% (operator dial)."""
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

    plan = compute_kasa_targets(
        equity=float(acc.get("equity") or 0),
        n_enabled=max(1, len(rows)),
        global_free_slots=int(cap.get("global_free_slots") or 0),
        margin_usage_pct=float(cap.get("margin_usage_pct") or 0),
        max_margin_usage_pct=float(
            sys.get("max_margin_usage_pct") or cap.get("max_margin_usage_pct") or 85),
        lot_multiplier=float(sys.get("lot_multiplier") or cap.get("lot_multiplier") or 1),
        max_concurrent_risk_pct=float(
            sys.get("max_concurrent_risk_pct") or cap.get("max_concurrent_risk_pct") or 50),
        zero_lot=zero_lot,
    )

    done: list[str] = [
        f"KASA eq ${plan['equity']:.0f} marj %{plan['margin_pct']:g} "
        f"inline lotx{plan['targets']['lot_multiplier']} "
        f"conc %{plan['targets']['max_concurrent_risk_pct']:g}",
    ]
    if zero_lot:
        done.append(f"UYARI {zero_lot} sembol lot=0")
    done.append("kasa_auto: lot/conc inline (marj dial operator)")
    return done
