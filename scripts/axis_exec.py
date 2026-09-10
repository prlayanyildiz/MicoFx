"""One charged-holdout axis tuner, for every gate axis that has one.

``adx_exec``, ``atr_pct_exec``, ``body_exec`` and ``cost_rank_exec`` were four
177-line files. Normalised for the field name they differed by nothing but two
things: which config key they tune and which candidate values they try. Every
threshold, the neighbour-support rule, the scoring replay, the pick order, the
POST and all four message shapes were byte-identical copies.

Four copies of a rule that decides live config is four places to fix a rule
and three places to miss. The measurement that started this found the same
shape in seven ``apply_*`` functions and six ``_score*`` functions.

What varies is an ``Axis``; what does not lives here once. ``msa_exec`` and
``trail_exec`` keep their own files: they are the same *shape* but not the
same rule (widen-only on the spread cap, an EXIT_RISK open-ticket skip on the
trail), and folding a different rule into a shared one is how the rule gets
lost.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from micofx.bar_snapshot import read, snapshot_path
from micofx.holdout_cost import charged_holdout
from micofx.models import SymbolConfig
from micofx.mt5client import timeframe_seconds
from scripts.session_exec import live_trade_sessions
from scripts.trail_exec import _neighbor_supported

# Shared accept thresholds. All four axes carried these same four numbers.
MIN_DELTA_R = 5.0
MIN_PF = 1.05
MAX_PF_DROP = 0.06
MAX_NEIGHBOR_GAP_R = 15.0


@dataclass(frozen=True)
class Axis:
    """One tunable gate axis.

    ``field`` is the SymbolConfig key and the key the pick is returned under.
    ``live_key`` is what the pick calls the current value - the four files
    each chose their own (``live_adx``, ``live_atr_pct``, ``live_body``,
    ``live_cr``) and callers read them by name, so they are kept verbatim.
    ``label`` is what the operator sees; ``cost_rank`` says ``cost_rank``, not
    ``cost_rank_max``.
    """

    field: str
    live_key: str
    candidates: tuple[float, ...]
    label: str = ""

    @property
    def name(self) -> str:
        return self.label or self.field


def best_axis_upgrade(
    axis: Axis,
    live_val: float,
    scored: dict[float, dict[str, Any] | None],
    *,
    min_delta_r: float = MIN_DELTA_R,
    max_pf_drop: float = MAX_PF_DROP,
    max_neighbor_gap_r: float = MAX_NEIGHBOR_GAP_R,
) -> dict[str, Any] | None:
    """The best candidate that clears every gate, or None to keep the live one.

    Gates, in order: it must beat live by ``min_delta_r``; hold PF above
    ``MIN_PF``; not drop PF more than ``max_pf_drop`` below live; and be
    neighbour-supported, so a single spike between two bad values cannot win.
    Ties go to the value closest to live - the smallest change that buys the
    improvement.
    """
    live_hold = None
    for val, hold in scored.items():
        if abs(float(val) - float(live_val)) < 1e-9 and isinstance(hold, dict):
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
        if abs(float(val) - float(live_val)) < 1e-9:
            continue
        try:
            net_r = float(hold.get("net_r") or 0.0)
            pf = float(hold.get("profit_factor") or 0.0)
        except (TypeError, ValueError):
            continue
        if net_r < live_r + min_delta_r - 1e-9:
            continue
        if pf < MIN_PF:
            continue
        if live_pf > 0 and pf + 1e-9 < live_pf - max_pf_drop:
            continue
        if not _neighbor_supported(
            float(val), scored, net_r, max_gap_r=max_neighbor_gap_r,
        ):
            continue
        key = (-net_r, abs(float(val) - float(live_val)))
        if best is None or key < best_key:
            best_key = key
            best = {
                axis.field: float(val),
                "net_r": net_r,
                "profit_factor": pf,
                "trades": hold.get("trades"),
                axis.live_key: float(live_val),
                "live_net_r": live_r,
                "live_pf": live_pf,
            }
    return best


def score_axis(
    axis: Axis, row: dict[str, Any], vals: tuple[float, ...],
) -> dict[float, dict[str, Any] | None]:
    """Replay the charged holdout once per candidate value.

    The overlay carries the row's own live session mask rather than whatever
    the snapshot was captured under, so the numbers describe the config as it
    trades today.
    """
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
        overlay[axis.field] = float(val)
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


def propose_axis_upgrade(axis: Axis, row: dict[str, Any]) -> dict[str, Any] | None:
    from scripts.exec_gates import gate_pick

    try:
        live_val = float(row.get(axis.field) or 0.0)
    except (TypeError, ValueError):
        return None
    vals = tuple(sorted(set(axis.candidates) | {live_val}))
    return gate_pick(
        row, best_axis_upgrade(axis, live_val, score_axis(axis, row, vals)),
        field=axis.field, value_key=axis.field)


def apply_axis_upgrade(
    axis: Axis,
    headers: dict[str, str],
    *,
    panel: str,
    row: dict[str, Any],
    propose: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
) -> tuple[bool, str]:
    """Land the pick through /api/opt/apply, or say nothing changed.

    ``force`` with the live score: this is a gate overlay on an already
    stamped config, not a fresh candidate, so it must not restamp the score.

    ``propose`` is the seam. Each axis module passes its own
    ``propose_<axis>_upgrade``, so that function stays the single point the
    apply path goes through - overridable, and patchable by the write-scope
    tests, which is how the first version of this merge was caught calling
    straight past it.
    """
    sym = str(row.get("symbol") or "")
    picker = propose or (lambda r: propose_axis_upgrade(axis, r))
    pick = picker(row)
    if pick is None:
        try:
            cur = float(row.get(axis.field) or 0.0)
        except (TypeError, ValueError):
            cur = 0.0
        return True, f"{sym} {axis.name} degismedi ({cur:g})"

    val = float(pick[axis.field])
    try:
        live_score = float(row.get("opt_score") or 0.0)
    except (TypeError, ValueError):
        live_score = 0.0
    payload = {
        "symbol": sym,
        "params": {axis.field: val},
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
        return False, f"{sym} {axis.name} fail: {exc.read().decode()[:100]}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"{sym} {axis.name} fail: {exc}"

    return True, (
        f"{sym} {axis.name} {pick[axis.live_key]:g}->{val:g} "
        f"({pick['live_net_r']:+.1f}R->{pick['net_r']:+.1f}R)"
    )
