"""trail_step_atr upgrades from charged holdout — exit axis only.

Neighbor-spike gate rejects US30-style grid-edge jumps where both adjacent
steps collapse while the challenger prints a hollow +R (04.09 measure).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from micofx.bar_snapshot import read, snapshot_path
from micofx.holdout_cost import charged_holdout
from micofx.models import SymbolConfig
from micofx.mt5client import timeframe_seconds
from scripts.axis_exec import (
    Axis,
    _neighbor_supported,
    apply_axis_upgrade,
)
from scripts.session_exec import live_trade_sessions

# Dense enough to catch local plateaus; includes live extras (JPN 2.8/3.2/3.6).
TRAIL_STEP_CANDIDATES: tuple[float, ...] = (
    0.4, 0.6, 0.8, 1.0, 1.2, 1.6, 1.8, 2.0, 2.2, 2.5, 2.8, 3.2, 3.6,
)
TRAIL_START_CANDIDATES: tuple[float, ...] = (
    0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0,
)
_MIN_DELTA_R = 8.0
_MIN_PF = 1.05
_MAX_PF_DROP = 0.10
# Challenger must have ≥1 scored neighbor within this many R (else edge spike).
_MAX_NEIGHBOR_GAP_R = 15.0


def best_trail_upgrade(
    live_step: float,
    scored: dict[float, dict[str, Any] | None],
    *,
    min_delta_r: float = _MIN_DELTA_R,
    max_pf_drop: float = _MAX_PF_DROP,
    max_neighbor_gap_r: float = _MAX_NEIGHBOR_GAP_R,
) -> dict[str, Any] | None:
    """Pick a charged-better trail_step_atr than ``live_step``, or None."""
    live_hold = None
    for step, hold in scored.items():
        if abs(float(step) - float(live_step)) < 1e-9 and isinstance(hold, dict):
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
    for step, hold in scored.items():
        if not isinstance(hold, dict):
            continue
        if abs(float(step) - float(live_step)) < 1e-9:
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
            float(step), scored, net_r, max_gap_r=max_neighbor_gap_r,
        ):
            continue
        key = (-net_r, abs(float(step) - float(live_step)))
        if best is None or key < best_key:
            best_key = key
            best = {
                "trail_step_atr": float(step),
                "net_r": net_r,
                "profit_factor": pf,
                "trades": hold.get("trades"),
                "live_step": float(live_step),
                "live_net_r": live_r,
                "live_pf": live_pf,
            }
    return best


def _score_axis(
    row: dict[str, Any],
    field: str,
    values: tuple[float, ...],
) -> dict[float, dict[str, Any] | None]:
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
    for val in values:
        overlay = deepcopy(row)
        for k in ("available", "digits", "description"):
            overlay.pop(k, None)
        overlay[field] = float(val)
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


def _score_steps(
    row: dict[str, Any], steps: tuple[float, ...],
) -> dict[float, dict[str, Any] | None]:
    return _score_axis(row, "trail_step_atr", steps)


def propose_trail_upgrade(row: dict[str, Any]) -> dict[str, Any] | None:
    from scripts.exec_gates import gate_pick
    try:
        live_step = float(row.get("trail_step_atr") or 0.0)
    except (TypeError, ValueError):
        return None
    if live_step <= 0:
        return None
    steps = tuple(sorted(set(TRAIL_STEP_CANDIDATES) | {live_step}))
    scored = _score_steps(row, steps)
    return gate_pick(
        row, best_trail_upgrade(live_step, scored),
        field="trail_step_atr", value_key="trail_step_atr")


def propose_trail_start_upgrade(row: dict[str, Any]) -> dict[str, Any] | None:
    from scripts.exec_gates import gate_pick
    try:
        live_start = float(row.get("trail_start_atr") or 0.0)
    except (TypeError, ValueError):
        return None
    if live_start <= 0:
        return None
    starts = tuple(sorted(set(TRAIL_START_CANDIDATES) | {live_start}))
    scored = _score_axis(row, "trail_start_atr", starts)
    return gate_pick(
        row, best_trail_start_upgrade(live_start, scored),
        field="trail_start_atr", value_key="trail_start_atr")


_STEP_AXIS = Axis(field="trail_step_atr", live_key="live_step",
                  candidates=TRAIL_STEP_CANDIDATES, label="trail_step")


def apply_trail_upgrade(
    headers: dict[str, str], *, panel: str, row: dict[str, Any],
) -> tuple[bool, str]:
    """Force gate-only apply. The POST half is shared
    (axis_exec.apply_axis_upgrade); the *rule* that picks the value
    stays in this file, because it is not the shared one.
    """
    return apply_axis_upgrade(_STEP_AXIS, headers, panel=panel, row=row,
                              propose=propose_trail_upgrade)


def best_trail_start_upgrade(
    live_start: float,
    scored: dict[float, dict[str, Any] | None],
    *,
    min_delta_r: float = _MIN_DELTA_R,
    max_pf_drop: float = _MAX_PF_DROP,
    max_neighbor_gap_r: float = _MAX_NEIGHBOR_GAP_R,
) -> dict[str, Any] | None:
    """Pick a charged-better trail_start_atr than ``live_start``, or None."""
    pick = best_trail_upgrade(
        live_start, scored,
        min_delta_r=min_delta_r,
        max_pf_drop=max_pf_drop,
        max_neighbor_gap_r=max_neighbor_gap_r,
    )
    if pick is None:
        return None
    return {
        "trail_start_atr": float(pick["trail_step_atr"]),
        "net_r": pick["net_r"],
        "profit_factor": pick["profit_factor"],
        "trades": pick.get("trades"),
        "live_start": float(pick["live_step"]),
        "live_net_r": pick["live_net_r"],
        "live_pf": pick["live_pf"],
    }


_START_AXIS = Axis(field="trail_start_atr", live_key="live_start",
                   candidates=TRAIL_START_CANDIDATES, label="trail_start")


def apply_trail_start_upgrade(
    headers: dict[str, str], *, panel: str, row: dict[str, Any],
) -> tuple[bool, str]:
    """Force gate-only apply. The POST half is shared
    (axis_exec.apply_axis_upgrade); the *rule* that picks the value
    stays in this file, because it is not the shared one.
    """
    return apply_axis_upgrade(_START_AXIS, headers, panel=panel, row=row,
                              propose=propose_trail_start_upgrade)


