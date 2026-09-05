"""max_spread_atr upgrades from charged holdout — entry gate only."""
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

# Shared cost-axis grid (same spirit as defaults / F50).
MSA_CANDIDATES: tuple[float, ...] = (0.03, 0.05, 0.08, 0.10, 0.12, 0.18)
_MIN_DELTA_R = 5.0
_MIN_PF = 1.05
# Challenger PF must stay close to live (0.05→0.08 SpotBrent 14-22: +40R but
# PF 1.23→1.14 / exp 0.144→0.084 / dd 24→35 — quantity over quality).
_MAX_PF_DROP = 0.06
_MIN_EXP_RATIO = 0.80
_MAX_DD_RATIO = 1.35


def best_msa_upgrade(
    live_msa: float,
    scored: dict[float, dict[str, Any] | None],
    *,
    min_delta_r: float = _MIN_DELTA_R,
    max_pf_drop: float = _MAX_PF_DROP,
    min_exp_ratio: float = _MIN_EXP_RATIO,
    max_dd_ratio: float = _MAX_DD_RATIO,
) -> dict[str, Any] | None:
    """Pick a charged-better max_spread_atr than ``live_msa``, or None."""
    live_hold = None
    for cap, hold in scored.items():
        if abs(float(cap) - float(live_msa)) < 1e-9 and isinstance(hold, dict):
            live_hold = hold
            break
    if live_hold is None:
        return None
    try:
        live_r = float(live_hold.get("net_r") or 0.0)
        live_pf = float(live_hold.get("profit_factor") or 0.0)
        live_exp = float(live_hold.get("expectancy") or 0.0)
        live_dd = float(live_hold.get("max_dd_r") or 0.0)
    except (TypeError, ValueError):
        return None

    best: dict[str, Any] | None = None
    best_key = (-1.0, float("inf"))  # max net_r, then min |cap-live| modest
    for cap, hold in scored.items():
        if not isinstance(hold, dict):
            continue
        if abs(float(cap) - float(live_msa)) < 1e-9:
            continue
        try:
            net_r = float(hold.get("net_r") or 0.0)
            pf = float(hold.get("profit_factor") or 0.0)
            exp = float(hold.get("expectancy") or 0.0)
            dd = float(hold.get("max_dd_r") or 0.0)
        except (TypeError, ValueError):
            continue
        if net_r < live_r + min_delta_r - 1e-9:
            continue
        if pf < _MIN_PF:
            continue
        if live_pf > 0 and pf + 1e-9 < live_pf - max_pf_drop:
            continue
        if live_exp > 0 and exp + 1e-9 < live_exp * min_exp_ratio:
            continue
        if live_dd > 0 and dd > live_dd * max_dd_ratio + 1e-9:
            continue
        key = (-net_r, abs(float(cap) - float(live_msa)))
        if best is None or key < best_key:
            best_key = key
            best = {
                "max_spread_atr": float(cap),
                "net_r": net_r,
                "profit_factor": pf,
                "trades": hold.get("trades"),
                "live_msa": float(live_msa),
                "live_net_r": live_r,
                "live_pf": live_pf,
            }
    return best


def _score_msa(row: dict[str, Any], caps: tuple[float, ...]) -> dict[float, dict[str, Any] | None]:
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
    for cap in caps:
        overlay = deepcopy(row)
        for k in ("available", "digits", "description"):
            overlay.pop(k, None)
        overlay["max_spread_atr"] = float(cap)
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
            out[float(cap)] = res.as_dict()
        except Exception:
            out[float(cap)] = None
    return out


def propose_msa_upgrade(row: dict[str, Any]) -> dict[str, Any] | None:
    from scripts.exec_gates import gate_pick
    try:
        live_msa = float(row.get("max_spread_atr") or 0.0)
    except (TypeError, ValueError):
        return None
    caps = tuple(sorted(set(MSA_CANDIDATES) | {live_msa}))
    scored = _score_msa(row, caps)
    return gate_pick(
        row, best_msa_upgrade(live_msa, scored),
        field="max_spread_atr", value_key="max_spread_atr")


def apply_msa_upgrade(
    headers: dict[str, str],
    *,
    panel: str,
    row: dict[str, Any],
) -> tuple[bool, str]:
    """Force gate-only msa write + charged restamp (narrow or widen)."""
    sym = str(row.get("symbol") or "")
    pick = propose_msa_upgrade(row)
    if pick is None:
        try:
            cur = float(row.get("max_spread_atr") or 0.0)
        except (TypeError, ValueError):
            cur = 0.0
        return True, f"{sym} msa degismedi ({cur:g})"

    cap = float(pick["max_spread_atr"])
    try:
        live_score = float(row.get("opt_score") or 0.0)
    except (TypeError, ValueError):
        live_score = 0.0
    payload = {
        "symbol": sym,
        "params": {"max_spread_atr": cap},
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
        return False, f"{sym} msa fail: {exc.read().decode()[:100]}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{sym} msa fail: {exc}"

    return True, (
        f"{sym} msa {pick['live_msa']:g}->{cap:g} "
        f"({pick['live_net_r']:+.1f}R->{pick['net_r']:+.1f}R)"
    )
