"""Spread execution helpers — widen entry gate without swapping family/TF."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

FAM = frozenset({"burst", "mtf_pullback", "ichimoku", "channel_break"})
_MIN_HOLDOUT_R = 15.0


def best_widen_run(history: list[dict[str, Any]], current_cap: float) -> dict[str, Any] | None:
    """Validated run with wider max_spread_atr and decent holdout, same or any family."""
    best: dict[str, Any] | None = None
    best_key = (-1.0, -1.0)
    for row in history:
        if row.get("strategy") not in FAM or not row.get("validated"):
            continue
        cap = float((row.get("params") or {}).get("max_spread_atr") or 0.0)
        if cap <= current_cap + 1e-9:
            continue
        hold_r = float((row.get("holdout") or {}).get("net_r") or 0.0)
        if hold_r < _MIN_HOLDOUT_R:
            continue
        key = (cap, hold_r)
        if key > best_key:
            best_key = key
            best = row
    return best


def apply_spread_widen(
    headers: dict[str, str],
    *,
    panel: str,
    symbol: str,
    current_cap: float,
    history: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Calibrate first; if unchanged, gates_only widen from opt history."""
    h = {**headers, "Origin": panel, "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(
            f"{panel}/api/symbols/{symbol}/spread-calibrate",
            data=b"{}", headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
        if body.get("changed"):
            return True, f"{symbol} spread {body.get('before')}->{body.get('after')} kalibre"
    except urllib.error.HTTPError as exc:
        if exc.code not in (404, 409):
            return False, f"{symbol} kalibre fail: {exc.read().decode()[:80]}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{symbol} kalibre fail: {exc}"

    row = best_widen_run(history, current_cap)
    if row is None:
        return True, f"{symbol} spread tavan degismedi ({current_cap:g})"

    cap = float((row.get("params") or {}).get("max_spread_atr") or 0.0)
    payload = json.dumps({
        "symbol": symbol,
        "run_id": int(row["id"]),
        "params": {"max_spread_atr": cap},
        "force": True,
        "gates_only": True,
    }).encode()
    try:
        req = urllib.request.Request(
            f"{panel}/api/opt/apply", data=payload, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            json.loads(resp.read().decode())
        return True, f"{symbol} spread {current_cap:g}->{cap:g} gates_only (run {row['id']})"
    except urllib.error.HTTPError as exc:
        return False, f"{symbol} spread widen fail: {exc.read().decode()[:100]}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{symbol} spread widen fail: {exc}"
