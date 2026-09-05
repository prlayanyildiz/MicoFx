"""Session-window upgrades from charged holdout — no family/TF swap."""
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
from micofx.optimizer import SEARCH_SESSION_WINDOWS, _is_all_hours_sessions, _sessions_key

_MIN_DELTA_R = 5.0
_MIN_PF = 1.05
# Challenger PF must stay within this of the live clock (reject net↑ / PF↓).
_MAX_PF_DROP = 0.12


def live_trade_sessions(row: dict[str, Any]) -> list[dict[str, str]]:
    """Window the engine actually trades (not a leftover sessions list)."""
    if not bool(row.get("use_sessions", True)):
        return [{"start": "00:00", "end": "23:59"}]
    sessions = row.get("sessions")
    if isinstance(sessions, list) and sessions:
        return [
            {"start": str(s.get("start")), "end": str(s.get("end"))}
            for s in sessions if isinstance(s, dict)
        ]
    return [{"start": "00:00", "end": "23:59"}]


def best_session_upgrade(
    live: list[dict[str, str]],
    scored: list[tuple[list[dict[str, str]], dict[str, Any] | None]],
    *,
    min_delta_r: float = _MIN_DELTA_R,
    max_pf_drop: float = _MAX_PF_DROP,
) -> dict[str, Any] | None:
    """Pick a charged-better clock than ``live``, or None.

    Requires +min_delta_r net_r and PF not collapsing vs live.
    """
    live_key = _sessions_key(live)
    live_hold: dict[str, Any] | None = None
    for windows, hold in scored:
        if _sessions_key(windows) == live_key and isinstance(hold, dict):
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
    best_r = live_r
    for windows, hold in scored:
        if not isinstance(hold, dict):
            continue
        if _sessions_key(windows) == live_key:
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
        if net_r > best_r + 1e-9:
            best_r = net_r
            best = {
                "sessions": windows,
                "net_r": net_r,
                "profit_factor": pf,
                "trades": hold.get("trades"),
                "max_dd_r": hold.get("max_dd_r"),
                "live_net_r": live_r,
                "live_pf": live_pf,
                "use_sessions": not _is_all_hours_sessions(windows),
            }
    return best


def _score_windows(
    row: dict[str, Any],
    windows_list: list[list[dict[str, str]]],
) -> list[tuple[list[dict[str, str]], dict[str, Any] | None]]:
    sym = str(row.get("symbol") or "")
    tf = str(row.get("timeframe") or "")
    path = snapshot_path(sym, tf)
    if not path.exists():
        return []
    try:
        snap = read(path)
    except Exception:
        return []
    bars = snap["bars"]
    info = snap["info"]
    scored: list[tuple[list[dict[str, str]], dict[str, Any] | None]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for windows in windows_list:
        key = _sessions_key(windows)
        if key in seen:
            continue
        seen.add(key)
        overlay = deepcopy(row)
        for k in ("available", "digits", "description"):
            overlay.pop(k, None)
        overlay["sessions"] = windows
        overlay["use_sessions"] = not _is_all_hours_sessions(windows)
        try:
            cfg = SymbolConfig.from_dict(overlay)
            res, _, _ = charged_holdout(
                bars=bars, cfg=cfg, point=float(info["point"]),
                tick_value=float(info["tick_value"]),
                tick_size=float(info["tick_size"]),
                spread_scale=float(snap["spread_scale"]),
                min_stop=float(snap["min_stop"]),
                segments=int(snap["segments"]),
                trade_all_hours=bool(snap["trade_all_hours"]),
                day_end_flatten_min=int(snap["day_end_flatten_min"]),
                tf_seconds=timeframe_seconds(tf),
            )
            scored.append((windows, res.as_dict()))
        except Exception:
            scored.append((windows, None))
    return scored


def propose_session_upgrade(row: dict[str, Any]) -> dict[str, Any] | None:
    """Offline charged compare; returns patch payload fields or None."""
    from scripts.exec_gates import charged_slice_nets, pipeline_frozen, upgrade_robust

    if pipeline_frozen():
        return None
    live = live_trade_sessions(row)
    windows_list = list(SEARCH_SESSION_WINDOWS)
    if _sessions_key(live) not in {_sessions_key(w) for w in windows_list}:
        windows_list = [live, *windows_list]
    scored = _score_windows(row, windows_list)
    pick = best_session_upgrade(live, scored)
    if pick is None:
        return None
    challenger = deepcopy(row)
    challenger["sessions"] = pick["sessions"]
    challenger["use_sessions"] = bool(pick["use_sessions"])
    if not upgrade_robust(
        charged_slice_nets(row), charged_slice_nets(challenger),
    ):
        return None
    return pick

def apply_session_upgrade(
    headers: dict[str, str],
    *,
    panel: str,
    row: dict[str, Any],
) -> tuple[bool, str]:
    """POST a charged-better session window; live restamp follows clock change."""
    sym = str(row.get("symbol") or "")
    pick = propose_session_upgrade(row)
    if pick is None:
        live = live_trade_sessions(row)
        label = f"{live[0].get('start')}-{live[0].get('end')}" if live else "?"
        return True, f"{sym} seans degismedi ({label})"

    payload = {
        "sessions": pick["sessions"],
        "use_sessions": bool(pick["use_sessions"]),
    }
    body = json.dumps(payload).encode()
    h = {**headers, "Origin": panel, "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(
            f"{panel}/api/symbols/{sym}", data=body, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=180) as resp:
            json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return False, f"{sym} seans fail: {exc.read().decode()[:100]}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{sym} seans fail: {exc}"

    win = pick["sessions"][0] if pick["sessions"] else {}
    label = f"{win.get('start')}-{win.get('end')}"
    return True, (
        f"{sym} seans -> {label} "
        f"({pick['live_net_r']:+.1f}R->{pick['net_r']:+.1f}R)"
    )
