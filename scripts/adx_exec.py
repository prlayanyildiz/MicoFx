"""adx_min upgrades from charged holdout — entry filter only."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from copy import deepcopy
from typing import Any

from micofx.bar_snapshot import read, snapshot_path
from micofx.holdout_cost import charged_holdout
from micofx.models import SymbolConfig
from micofx.mt5client import timeframe_seconds
from scripts.session_exec import live_trade_sessions
from scripts.trail_exec import _neighbor_supported

ADX_MIN_CANDIDATES: tuple[float, ...] = (0.0, 10.0, 12.0, 15.0, 18.0, 20.0, 22.0, 25.0)
_MIN_DELTA_R = 5.0
_MIN_PF = 1.05
_MAX_PF_DROP = 0.06
_MAX_NEIGHBOR_GAP_R = 15.0


def best_adx_upgrade(
    live_adx: float,
    scored: dict[float, dict[str, Any] | None],
    *,
    min_delta_r: float = _MIN_DELTA_R,
    max_pf_drop: float = _MAX_PF_DROP,
    max_neighbor_gap_r: float = _MAX_NEIGHBOR_GAP_R,
) -> dict[str, Any] | None:
    live_hold = None
    for val, hold in scored.items():
        if abs(float(val) - float(live_adx)) < 1e-9 and isinstance(hold, dict):
            live_hold = hold
            break
    if live_hold is None:
        return None
    try:
        live_r = float(live_hold.get("net_r") or 0.0)
        live_pf = float(live_hold.get("profit_factor") or 0.0)
    except (TypeError, ValueError):
        return None

    best: dict[str, Any] | None = None
    best_key = (-1.0, float("inf"))
    for val, hold in scored.items():
        if not isinstance(hold, dict):
            continue
        if abs(float(val) - float(live_adx)) < 1e-9:
            continue
        try:
            net_r = float(hold.get("net_r") or 0.0)
            pf = float(hold.get("profit_factor") or 0.0)
        except (TypeError, ValueError):
            continue
        if net_r < live_r + min_delta_r - 1e-9:
            continue
        if pf < _MIN_PF:
            continue
        if live_pf > 0 and pf + 1e-9 < live_pf - max_pf_drop:
            continue
        if not _neighbor_supported(
            float(val), scored, net_r, max_gap_r=max_neighbor_gap_r,
        ):
            continue
        key = (-net_r, abs(float(val) - float(live_adx)))
        if best is None or key < best_key:
            best_key = key
            best = {
                "adx_min": float(val),
                "net_r": net_r,
                "profit_factor": pf,
                "trades": hold.get("trades"),
                "live_adx": float(live_adx),
                "live_net_r": live_r,
                "live_pf": live_pf,
            }
    return best


def _score_adx(row: dict[str, Any], vals: tuple[float, ...]) -> dict[float, dict[str, Any] | None]:
    sym = str(row.get("symbol") or "")
    tf = str(row.get("timeframe") or "")
    path = snapshot_path(sym, tf)
    if not path.exists():
        return {}
    try:
        snap = read(path)
    except Exception:
        return {}
    live_sess = live_trade_sessions(row)
    out: dict[float, dict[str, Any] | None] = {}
    for val in vals:
        overlay = deepcopy(row)
        for k in ("available", "digits", "description"):
            overlay.pop(k, None)
        overlay["adx_min"] = float(val)
        if not bool(row.get("use_sessions", True)):
            overlay["use_sessions"] = False
        else:
            overlay["sessions"] = live_sess
            overlay["use_sessions"] = True
        try:
            cfg = SymbolConfig.from_dict(overlay)
            res, _, _ = charged_holdout(
                bars=snap["bars"], cfg=cfg,
                point=float(snap["info"]["point"]),
                tick_value=float(snap["info"]["tick_value"]),
                tick_size=float(snap["info"]["tick_size"]),
                spread_scale=float(snap["spread_scale"]),
                min_stop=float(snap["min_stop"]),
                segments=int(snap["segments"]),
                trade_all_hours=bool(snap["trade_all_hours"]),
                day_end_flatten_min=int(snap["day_end_flatten_min"]),
                tf_seconds=timeframe_seconds(tf),
            )
            out[float(val)] = res.as_dict()
        except Exception:
            out[float(val)] = None
    return out


def propose_adx_upgrade(row: dict[str, Any]) -> dict[str, Any] | None:
    from scripts.exec_gates import gate_pick
    try:
        live_adx = float(row.get("adx_min") or 0.0)
    except (TypeError, ValueError):
        return None
    vals = tuple(sorted(set(ADX_MIN_CANDIDATES) | {live_adx}))
    return gate_pick(
        row, best_adx_upgrade(live_adx, _score_adx(row, vals)),
        field="adx_min", value_key="adx_min")


def apply_adx_upgrade(
    headers: dict[str, str],
    *,
    panel: str,
    row: dict[str, Any],
) -> tuple[bool, str]:
    sym = str(row.get("symbol") or "")
    pick = propose_adx_upgrade(row)
    if pick is None:
        try:
            cur = float(row.get("adx_min") or 0.0)
        except (TypeError, ValueError):
            cur = 0.0
        return True, f"{sym} adx_min degismedi ({cur:g})"

    val = float(pick["adx_min"])
    try:
        live_score = float(row.get("opt_score") or 0.0)
    except (TypeError, ValueError):
        live_score = 0.0
    payload = {
        "symbol": sym,
        "params": {"adx_min": val},
        "score": live_score,
        "force": True,
    }
    body = json.dumps(payload).encode()
    h = {**headers, "Origin": panel, "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(
            f"{panel}/api/opt/apply", data=body, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=180) as resp:
            json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return False, f"{sym} adx_min fail: {exc.read().decode()[:100]}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{sym} adx_min fail: {exc}"

    return True, (
        f"{sym} adx_min {pick['live_adx']:g}->{val:g} "
        f"({pick['live_net_r']:+.1f}R->{pick['net_r']:+.1f}R)"
    )
