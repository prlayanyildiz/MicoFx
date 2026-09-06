"""Compare full-history 6-slice vs charged_holdout last-segment for one field.

Prevents slice-sum-only false upgrades (XAU min_body 0.1 vs 0.3, 04.09).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from micofx.bar_snapshot import read, snapshot_path
from micofx.holdout_cost import charged_holdout
from micofx.models import SymbolConfig
from micofx.mt5client import timeframe_seconds
from scripts.exec_gates import charged_slice_nets, charged_slice_report, upgrade_robust
from scripts.session_exec import live_trade_sessions


def decide_windows(
    *,
    slice_live_sum: float | None,
    slice_chal_sum: float | None,
    slice_robust: bool | None,
    hold_live: float | None,
    hold_chal: float | None,
    min_delta_r: float = 5.0,
) -> str:
    """APPLY only when recent holdout AND full-slice both prefer challenger."""
    slice_prefers_chal = (
        slice_live_sum is not None
        and slice_chal_sum is not None
        and slice_chal_sum > slice_live_sum + min_delta_r
        and slice_robust is True
    )
    hold_prefers_chal = (
        hold_live is not None
        and hold_chal is not None
        and hold_chal > hold_live + min_delta_r
    )
    hold_prefers_live = (
        hold_live is not None
        and hold_chal is not None
        and hold_live + 1e-9 >= hold_chal
    )
    if hold_prefers_chal and slice_prefers_chal:
        return "APPLY"
    if hold_prefers_live and slice_prefers_chal:
        return "KEEP_CONFLICT_frontload"
    if hold_prefers_chal and not slice_prefers_chal:
        return "HOLD_ONLY_review"
    return "KEEP"


def field_window_compare(
    row: dict[str, Any],
    *,
    field: str,
    challenger: float,
) -> dict[str, Any]:
    """Return slice + holdout scores for live vs challenger; recommend action."""
    sym = str(row.get("symbol") or "")
    tf = str(row.get("timeframe") or "")
    try:
        live_v = float(row.get(field) or 0.0)
    except (TypeError, ValueError):
        live_v = 0.0
    try:
        chal_v = float(challenger)
    except (TypeError, ValueError):
        return {"ok": False, "error": "bad challenger"}

    live_rep = charged_slice_report(row)
    chal_rep = charged_slice_report(row, field=field, value=chal_v)
    slice_robust = None
    if abs(chal_v - live_v) > 1e-12:
        slice_robust = upgrade_robust(
            charged_slice_nets(row),
            charged_slice_nets(row, field=field, value=chal_v),
        )

    path = snapshot_path(sym, tf)
    hold_live = hold_chal = None
    hold_lo = hold_hi = segs = None
    if path.is_file():
        snap = read(path)
        segs = int(snap["segments"])
        live_sess = live_trade_sessions(row)

        def _hold(val: float) -> float:
            nonlocal hold_lo, hold_hi
            overlay = deepcopy(row)
            for k in ("available", "digits", "description"):
                overlay.pop(k, None)
            overlay[field] = float(val)
            if not bool(row.get("use_sessions", True)):
                overlay["use_sessions"] = False
            else:
                overlay["sessions"] = live_sess
                overlay["use_sessions"] = True
            cfg = SymbolConfig.from_dict(overlay)
            res, lo, hi = charged_holdout(
                bars=snap["bars"], cfg=cfg,
                point=float(snap["info"]["point"]),
                tick_value=float(snap["info"]["tick_value"]),
                tick_size=float(snap["info"]["tick_size"]),
                spread_scale=float(snap["spread_scale"]),
                min_stop=float(snap["min_stop"]),
                segments=segs,
                trade_all_hours=bool(snap["trade_all_hours"]),
                day_end_flatten_min=int(snap["day_end_flatten_min"]),
                tf_seconds=timeframe_seconds(tf),
            )
            hold_lo, hold_hi = lo, hi
            return float(res.net_r)

        hold_live = _hold(live_v)
        hold_chal = _hold(chal_v)

    live_sum = round(sum(live_rep["nets"]), 2) if live_rep else None
    chal_sum = round(sum(chal_rep["nets"]), 2) if chal_rep else None
    last_live = (
        round(float(live_rep["nets"][-1]), 2)
        if live_rep and live_rep.get("nets") else None
    )
    last_chal = (
        round(float(chal_rep["nets"][-1]), 2)
        if chal_rep and chal_rep.get("nets") else None
    )

    decision = decide_windows(
        slice_live_sum=live_sum,
        slice_chal_sum=chal_sum,
        slice_robust=slice_robust,
        hold_live=hold_live,
        hold_chal=hold_chal,
    )
    return {
        "ok": True,
        "symbol": sym,
        "field": field,
        "live": live_v,
        "challenger": chal_v,
        "slice": {
            "live_sum": live_sum,
            "chal_sum": chal_sum,
            "last_live": last_live,
            "last_chal": last_chal,
            "upgrade_robust": slice_robust,
        },
        "holdout_last_seg": {
            "live_net_r": round(hold_live, 2) if hold_live is not None else None,
            "chal_net_r": round(hold_chal, 2) if hold_chal is not None else None,
            "lo": hold_lo,
            "hi": hold_hi,
            "segments": segs,
        },
        "decision": decision,
        "note": (
            "APPLY needs holdout AND slice agreement. "
            "KEEP_CONFLICT_frontload = slice sum up but recent edge not."
        ),
    }
