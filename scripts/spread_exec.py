"""Spread execution helpers — widen entry gate without swapping family/TF."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from micofx.models import STRATEGIES

FAM = frozenset(STRATEGIES)
_MIN_HOLDOUT_R = 15.0


def best_widen_run(
    history: list[dict[str, Any]],
    current_cap: float,
    *,
    strategy: str | None = None,
    live_hold_r: float | None = None,
) -> dict[str, Any] | None:
    """Validated run with wider max_spread_atr and decent holdout.

    Prefers higher holdout net_r; on a tie takes the *smallest* wider cap so a
    0.08→0.12 jump does not beat a measured 0.10 sweet spot (US30 Claude).

    When ``strategy`` is set, only that family counts — gates_only keeps the
    live family, so a burst +68R stamp must not justify widening an mtf row.

    ``live_hold_r`` (when set) is a floor: a wider history row that stamps
    weaker than the live book must not undo a measured tighten (NAS100
    0.05/+103 must not re-widen to 0.08/+99 from older burst history).
    """
    want = str(strategy or "")
    floor = _MIN_HOLDOUT_R
    if live_hold_r is not None:
        try:
            floor = max(floor, float(live_hold_r))
        except (TypeError, ValueError):
            pass
    best: dict[str, Any] | None = None
    best_key = (-1.0, float("inf"))
    for row in history:
        fam = str(row.get("strategy") or "")
        if fam not in FAM or not row.get("validated"):
            continue
        if want and fam != want:
            continue
        cap = float((row.get("params") or {}).get("max_spread_atr") or 0.0)
        if cap <= current_cap + 1e-9:
            continue
        hold_r = float((row.get("holdout") or {}).get("net_r") or 0.0)
        if hold_r < floor - 1e-9:
            continue
        # Maximize hold_r, then minimize cap (modest widen).
        key = (-hold_r, cap)
        if best is None or key < best_key:
            best_key = key
            best = row
    return best


def _live_holdout_r(row: dict[str, Any] | None) -> float | None:
    if not isinstance(row, dict):
        return None
    for blob in (row.get("holdout_costed"), row.get("holdout"),
                 (row.get("opt_summary") or {}).get("holdout")
                 if isinstance(row.get("opt_summary"), dict) else None):
        if not isinstance(blob, dict):
            continue
        try:
            return float(blob.get("net_r"))
        except (TypeError, ValueError):
            continue
    return None


def _live_symbol_row(
    headers: dict[str, str], panel: str, symbol: str,
) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(
            f"{panel}/api/symbols", headers={**headers, "Origin": panel})
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    rows = body.get("symbols") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("symbol") == symbol:
            return row
    return None


def _live_max_spread(headers: dict[str, str], panel: str, symbol: str) -> float | None:
    row = _live_symbol_row(headers, panel, symbol)
    if row is None:
        return None
    try:
        return float(row.get("max_spread_atr") or 0.0)
    except (TypeError, ValueError):
        return None


def _live_strategy(headers: dict[str, str], panel: str, symbol: str) -> str | None:
    row = _live_symbol_row(headers, panel, symbol)
    if row is None:
        return None
    fam = str(row.get("strategy") or "")
    return fam if fam in FAM else None


def apply_spread_widen(
    headers: dict[str, str],
    *,
    panel: str,
    symbol: str,
    current_cap: float,
    history: list[dict[str, Any]],
    strategy: str | None = None,
) -> tuple[bool, str]:
    """gates_only widen from same-family opt history (no band calibrate).

    Band calibrate is widen-only and undid NAS100 0.05→0.06 on 04.09 while
    charged preferred 0.05. In-process ``_recalibrate_spread_cap`` now has a
    charged non-regress gate; this HTTP helper stays history-only.
    """
    from scripts.exec_gates import pipeline_frozen
    if pipeline_frozen():
        return True, f"{symbol} spread: exec pipeline FREEZE"
    h = {**headers, "Origin": panel, "Content-Type": "application/json"}
    live_row = _live_symbol_row(headers, panel, symbol)
    live_strat = strategy
    if not live_strat:
        fam = str((live_row or {}).get("strategy") or "")
        live_strat = fam if fam in FAM else None
    live_hold = _live_holdout_r(live_row)
    row = best_widen_run(
        history, current_cap, strategy=live_strat, live_hold_r=live_hold)
    if row is None:
        return True, f"{symbol} spread tavan degismedi ({current_cap:g})"

    cap = float((row.get("params") or {}).get("max_spread_atr") or 0.0)
    # 6-slice non-erosion (Claude 04.09 — last auto-adjust path).
    if isinstance(live_row, dict) and cap > float(current_cap) + 1e-9:
        try:
            from scripts.exec_gates import charged_slice_nets, upgrade_robust
            live_nets = charged_slice_nets(live_row)
            chal_nets = charged_slice_nets(
                live_row, field="max_spread_atr", value=cap)
            if not upgrade_robust(
                live_nets, chal_nets, min_full_delta_r=-1.0,
            ):
                return True, (
                    f"{symbol} spread tavan degismedi ({current_cap:g}) "
                    f"— 6-slice erozyon ({current_cap:g}->{cap:g})"
                )
        except Exception:
            pass

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
        # Charged restamp after gates_only can exceed 120s on a cold bar window.
        with urllib.request.urlopen(req, timeout=180) as resp:
            json.loads(resp.read().decode())
        return True, f"{symbol} spread {current_cap:g}->{cap:g} gates_only (run {row['id']})"
    except urllib.error.HTTPError as exc:
        live = _live_max_spread(headers, panel, symbol)
        if live is not None and live + 1e-9 >= cap:
            # Apply wrote then the HTTP layer errored (US30 0.08→0.12 still LAND).
            return True, (f"{symbol} spread {current_cap:g}->{live:g} "
                          f"gates_only (run {row['id']}, HTTP {exc.code} sonrasi teyit)")
        return False, f"{symbol} spread widen fail: {exc.read().decode()[:100]}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        live = _live_max_spread(headers, panel, symbol)
        if live is not None and live + 1e-9 >= cap:
            return True, (f"{symbol} spread {current_cap:g}->{live:g} "
                          f"gates_only (run {row['id']}, timeout sonrasi teyit)")
        return False, f"{symbol} spread widen fail: {exc}"
