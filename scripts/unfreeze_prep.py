"""Unfreeze-prep metrics — Claude 10:14 criteria board (report-only).

Tracks premature-stop / fill / 6-slice / baseline progress while exec is
FROZEN. Does not unfreeze. Written so the 25-close review has a stamp trail.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
OUT_PATH = ROOT / ".bridge" / "UNFREEZE_PREP.json"
BOOK = ("BTCUSD", "GER40", "JPN225", "NAS100", "SpotBrent", "US30", "XAUUSD")
FILL_FOCUS = ("GER40", "US30", "NAS100")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def frozen() -> bool:
    return (ROOT / ".bridge" / "EXEC_PIPELINE_FROZEN").is_file()


def premature_by_symbol(rows: list[dict[str, Any]]) -> dict[str, int]:
    from micofx.optimizer import premature_sl_count_from_autopsy

    return {s: int(premature_sl_count_from_autopsy(rows, s)) for s in BOOK}


def post_restart_rows(
    rows: list[dict[str, Any]], *, n_new: int,
) -> list[dict[str, Any]]:
    """Last ``n_new`` autopsy rows by broker exit_time epoch."""
    n = max(0, int(n_new))
    if n <= 0:
        return []

    def _exit_epoch(r: dict[str, Any]) -> int:
        try:
            return int(float(r.get("exit_time") or 0))
        except (TypeError, ValueError):
            return 0

    return sorted(rows, key=_exit_epoch)[-n:]


def premature_sl_metrics(
    rows: list[dict[str, Any]],
    *,
    min_recovery_r: float = 0.8,
    min_after_1h_bars: int = 3,
) -> dict[str, Any]:
    """Book-wide premature SL rate + window-sufficient lift (Claude 17:44).

    Official evidence@100 lift uses the same ``after_1h_bars >= K`` filter on
    both sides (default K=3). That drops dead session-end windows without
    proxying on exit_reason. Raw non-SL lift and lift_vs_all stay diagnostic.
    """
    try:
        floor = float(min_recovery_r)
    except (TypeError, ValueError):
        floor = 0.8
    try:
        k_bars = max(0, int(min_after_1h_bars))
    except (TypeError, ValueError):
        k_bars = 3

    def _accum(min_bars: int) -> tuple[int, int, int, int, int, int]:
        sl_d = sl_p = non_d = non_h = all_d = all_h = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            reason = str(row.get("exit_reason") or "").lower()
            try:
                bars = float(row.get("after_1h_bars") or 0)
            except (TypeError, ValueError):
                continue
            if bars < float(min_bars) or bars <= 0:
                continue
            through = bool(row.get("after_1h_through_entry"))
            try:
                rec = float(row.get("after_1h_recovery_r") or 0.0)
            except (TypeError, ValueError):
                rec = 0.0
            hit = through or rec + 1e-12 >= floor
            all_d += 1
            if hit:
                all_h += 1
            if reason == "sl":
                try:
                    realised = row.get("r_realised")
                    if realised is not None and not isinstance(realised, bool):
                        if float(realised) >= 0.0:
                            continue
                except (TypeError, ValueError):
                    pass
                sl_d += 1
                if hit:
                    sl_p += 1
            else:
                non_d += 1
                if hit:
                    non_h += 1
        return sl_d, sl_p, non_d, non_h, all_d, all_h

    sl_denom, sl_prem, non_sl_denom, non_sl_hit, all_denom, all_hit = _accum(k_bars)
    # Diagnostic: any positive window (old non-SL / vs-all defs).
    r_sl_d, r_sl_p, r_non_d, r_non_h, r_all_d, r_all_h = _accum(1)

    rate = (sl_prem / sl_denom) if sl_denom else None
    base_non = (non_sl_hit / non_sl_denom) if non_sl_denom else None
    base_all = (all_hit / all_denom) if all_denom else None
    rate_raw = (r_sl_p / r_sl_d) if r_sl_d else None
    base_non_raw = (r_non_h / r_non_d) if r_non_d else None
    base_all_raw = (r_all_h / r_all_d) if r_all_d else None

    lift = None
    lift_nonsl_raw = None
    lift_vs_all = None
    if rate is not None and base_non is not None and base_non > 1e-12:
        lift = round(rate / base_non, 3)
    if rate_raw is not None and base_non_raw is not None and base_non_raw > 1e-12:
        lift_nonsl_raw = round(rate_raw / base_non_raw, 3)
    if rate_raw is not None and base_all_raw is not None and base_all_raw > 1e-12:
        lift_vs_all = round(rate_raw / base_all_raw, 3)

    return {
        "sl_denom": sl_denom,
        "premature": sl_prem,
        "rate": round(rate, 4) if rate is not None else None,
        "non_sl_denom": non_sl_denom,
        "non_sl_recovery_rate": round(base_non, 4) if base_non is not None else None,
        "all_exit_denom": all_denom,
        "all_exit_recovery_rate": round(base_all, 4) if base_all is not None else None,
        "lift": lift,  # official: K>=min_after_1h_bars vs non-SL (Claude 17:44)
        "lift_nonsl_raw": lift_nonsl_raw,  # diagnostic: bars>0 vs non-SL
        "lift_vs_all": lift_vs_all,  # diagnostic: bars>0 vs all exits
        "min_recovery_r": floor,
        "min_after_1h_bars": k_bars,
        "historical_lift_ref": 1.437,
    }


def unfreeze_gate_frame(n_new: int) -> dict[str, Any]:
    """25 = safety checkpoint; 100 = evidence (Claude 17:06 power analysis)."""
    n = max(0, int(n_new))
    return {
        "n_new": n,
        "safety_at": 25,
        "evidence_at": 100,
        "phase": (
            "pre_safety" if n < 25
            else ("safety" if n < 100 else "evidence")
        ),
        "per_symbol_premature_floor": n >= 100,
        "premature_is_gate": n >= 100,
        "note": (
            "n=25: catastrophe check only (rate→1 / gate6 break / hard −R). "
            "Improvement claims need n≈100 (band ±0.10). "
            "Official lift uses after_1h_bars>=3 on both sides (Claude 17:44). "
            "Per-symbol premature floor off until 100."
        ),
    }


def trail_geometry(
    *,
    sl_atr_mult: float,
    trail_start_atr: float,
    trail_step_atr: float,
    breakeven_at_r: float = 0.0,
    symbol: str = "",
) -> dict[str, Any]:
    """Detect wide trail_step vs SL so trail cannot beat original stop early.

    Same identity as panel ``trail_improves_at_r`` / ``trail_arms_at_r``
    (``web/app.py``): trail places ``close ± step*ATR`` and only improves the
    hard SL once profit clears ``max(start, step - sl)`` ATR → that / sl in R.

    Wide geometry (monitor-only, AXIS_CLOSED_OPTIMUM): when BE is on,
    trail_improves_at_r > BE — stop stays at original SL through the BE zone
    (XAU 0.7/2.5 → ~2.57R > BE@1.5). When BE is off, flag improves_at_r > 2.0.
    Claude joint sl×step: this is OPTIMUM give-back cost, not a fix-trail
    defect. Never an unfreeze gate; ``trap`` key kept for compatibility.
    """
    try:
        sl = float(sl_atr_mult or 0.0)
    except (TypeError, ValueError):
        sl = 0.0
    try:
        ts = float(trail_start_atr or 0.0)
    except (TypeError, ValueError):
        ts = 0.0
    try:
        st = float(trail_step_atr or 0.0)
    except (TypeError, ValueError):
        st = 0.0
    try:
        be = float(breakeven_at_r or 0.0)
    except (TypeError, ValueError):
        be = 0.0
    if sl <= 0 or (ts <= 0 and st <= 0):
        return {
            "symbol": symbol,
            "sl_atr_mult": sl,
            "trail_start_atr": ts,
            "trail_step_atr": st,
            "breakeven_at_r": be,
            "need_mfe_atr_before_trail_beats_sl": None,
            "trail_improves_at_r": None,
            "trail_arms_at_r": None,
            "trap": False,
            "wide": False,
            "status": "ok",
            "why": "no_trail_or_sl",
            "monitor_only": True,
            "axis_status": "ok",
        }
    need_atr = max(ts, st - sl) if st > 0 else ts
    improves_r = need_atr / sl
    arms_r = max(ts, st) / sl
    if be > 0:
        trap = improves_r > be + 1e-12
        why = (
            f"wide geometry OPTIMUM: improves@{improves_r:.2f}R > BE@{be:g}; "
            f"give-back until trail beats SL (~{improves_r:.2f}R) — not a fix"
            if trap else "ok"
        )
    else:
        trap = improves_r > 2.0 + 1e-12
        why = (
            f"wide geometry OPTIMUM: no BE; improves@"
            f"{improves_r:.2f}R > 2.0 — not a fix"
            if trap else "ok"
        )
    return {
        "symbol": symbol,
        "sl_atr_mult": sl,
        "trail_start_atr": ts,
        "trail_step_atr": st,
        "breakeven_at_r": be,
        "need_mfe_atr_before_trail_beats_sl": round(need_atr, 4),
        "trail_improves_at_r": round(improves_r, 4),
        "trail_arms_at_r": round(arms_r, 4),
        "trap": bool(trap),
        "wide": bool(trap),
        "status": "OPTIMUM" if trap else "ok",
        "why": why,
        "monitor_only": True,
        "axis_status": "AXIS_CLOSED_OPTIMUM" if trap else "ok",
    }


def book_trail_geometry(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Book-wide trail geometry monitor (enabled BOOK symbols only).

    Surfaces wide step/SL ratios for visibility. Axis is
    AXIS_CLOSED_OPTIMUM (Claude joint sl×step) — do not imply fix-trail.
    """
    by: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or "")
        if sym not in BOOK:
            continue
        by[sym] = trail_geometry(
            symbol=sym,
            sl_atr_mult=row.get("sl_atr_mult", 0.0),
            trail_start_atr=row.get("trail_start_atr", 0.0),
            trail_step_atr=row.get("trail_step_atr", 0.0),
            breakeven_at_r=row.get("breakeven_at_r", 0.0),
        )
    traps = [s for s, g in sorted(by.items()) if g.get("trap")]
    return {
        "by_symbol": by,
        "trap_symbols": traps,  # compat; prefer wide_symbols
        "wide_symbols": traps,
        "n_trap": len(traps),
        "n_wide": len(traps),
        "is_gate": False,
        "axis_status": "AXIS_CLOSED_OPTIMUM",
        "label": "OPTIMUM",
        "note": (
            "MONITOR only — AXIS_CLOSED_OPTIMUM. Wide trail_step vs sl is "
            "measured give-back cost of runners, not a fix-trail defect. "
            "Not a gate."
        ),
    }


def give_back_post_restart(
    rows: list[dict[str, Any]],
    *,
    min_mfe_r: float = 0.5,
) -> dict[str, Any]:
    """Give-back / capture monitor on post-restart closes (Claude 12:04).

    NOT an unfreeze gate at n=25 (90% band ±0.25 — noise). Split by
    exit_reason so trail mix cannot fake improvement. Trail-only may become
    a gate around n~200. Rows with mfe_r < min_mfe_r skipped (no real peak).
    """
    by: dict[str, dict[str, float]] = {}
    by_exit: dict[str, dict[str, float]] = {}
    left_sum = 0.0
    mfe_sum = 0.0
    capt_num = 0.0  # sum r_realised where present
    capt_den = 0.0
    n = 0
    for r in rows:
        try:
            mfe = float(r.get("mfe_r") or 0.0)
            left = float(r.get("left_on_table_r") or 0.0)
        except (TypeError, ValueError):
            continue
        if mfe < float(min_mfe_r):
            continue
        sym = str(r.get("symbol") or "") or "?"
        reason = str(r.get("exit_reason") or r.get("reason") or "other").lower()
        if reason.startswith("trail"):
            reason = "trail"
        elif reason in ("sl", "stop", "stop_loss") or reason.startswith("sl"):
            reason = "sl"
        elif "flatten" in reason or reason in ("day_end", "session"):
            reason = "flatten"
        cell = by.setdefault(sym, {"n": 0.0, "left": 0.0, "mfe": 0.0})
        cell["n"] += 1
        cell["left"] += left
        cell["mfe"] += mfe
        ex = by_exit.setdefault(reason, {"n": 0.0, "left": 0.0, "mfe": 0.0,
                                         "r_sum": 0.0, "r_n": 0.0})
        ex["n"] += 1
        ex["left"] += left
        ex["mfe"] += mfe
        try:
            rr = float(r.get("r_realised") if r.get("r_realised") is not None
                       else r.get("r") or 0.0)
            ex["r_sum"] += rr
            ex["r_n"] += 1
            capt_num += rr
            capt_den += mfe
        except (TypeError, ValueError):
            pass
        left_sum += left
        mfe_sum += mfe
        n += 1

    def _ratio(left: float, mfe: float) -> float | None:
        return round(left / mfe, 4) if mfe > 0 else None

    def _cap(r_sum: float, mfe: float) -> float | None:
        return round(r_sum / mfe, 4) if mfe > 0 else None

    return {
        "n": n,
        "min_mfe_r": float(min_mfe_r),
        "left_sum": round(left_sum, 4),
        "mfe_sum": round(mfe_sum, 4),
        "ratio": _ratio(left_sum, mfe_sum),  # left_on_table / mfe (give-back)
        "capture_ratio": _cap(capt_num, capt_den) if capt_den > 0 else None,
        "by_symbol": {
            s: {
                "n": int(c["n"]),
                "ratio": _ratio(c["left"], c["mfe"]),
            }
            for s, c in sorted(by.items())
        },
        "by_exit": {
            k: {
                "n": int(c["n"]),
                "ratio": _ratio(c["left"], c["mfe"]),
                "capture": _cap(c["r_sum"], c["mfe"]) if c["r_n"] else None,
            }
            for k, c in sorted(by_exit.items())
        },
        "is_gate": False,
        "note": (
            "MONITOR only — not a 25-close unfreeze gate (Claude 12:04). "
            "Same power limit as premature_sl at n=25 (Claude 17:06). "
            "Trail-only may gate ~n200."
        ),
    }


def fill_focus(rows_eb: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    from scripts.us30_fill_watch import SOFT_BLOCKS

    out: dict[str, dict[str, Any]] = {}
    for row in rows_eb:
        sym = str(row.get("symbol") or "")
        if sym not in FILL_FOCUS:
            continue
        sig = int(row.get("signals") or 0)
        opened = int(row.get("opened") or 0)
        blocks = row.get("blocks") if isinstance(row.get("blocks"), dict) else {}
        hard = sum(
            int(v) for k, v in blocks.items() if str(k) not in SOFT_BLOCKS)
        actionable = opened + hard if blocks else max(0, sig)
        try:
            fill = float(row.get("fill_rate") or 0.0)
        except (TypeError, ValueError):
            fill = (opened / sig) if sig else 0.0
        action_fill = (opened / actionable) if actionable else 0.0
        out[sym] = {
            "signals": sig,
            "actionable_signals": actionable,
            "opened": opened,
            "fill_rate": round(fill, 4),
            "action_fill_rate": round(action_fill, 4),
            "spread_blocks": int(blocks.get("spread") or 0),
        }
    for s in FILL_FOCUS:
        out.setdefault(s, {
            "signals": 0,
            "actionable_signals": 0,
            "opened": 0,
            "fill_rate": 0.0,
            "action_fill_rate": 0.0,
            "spread_blocks": 0,
        })
    return out


def snapshot(
    *,
    panel: str = PANEL,
    out_path: Path | None = None,
) -> dict[str, Any]:
    from scripts import book_robust_audit as book_robust
    from scripts.xau_streak_watch import baseline_status, fetch_autopsy_rows

    rows = fetch_autopsy_rows(panel)
    bl = baseline_status(len(rows))
    prem = premature_by_symbol(rows)
    # Post-restart window: autopsy exit_time is broker epoch int, not ISO.
    # Align with baseline counter (autopsy_n - stamp), not string compare.
    n_new = max(0, int(bl.get("new_trades") or 0))
    post_rows = post_restart_rows(rows, n_new=n_new)
    prem_post = premature_by_symbol(post_rows) if post_rows else dict.fromkeys(BOOK, 0)
    # entry-blocks via book_robust panel cookie pattern
    import http.cookiejar

    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    eb_rows: list[dict[str, Any]] = []
    sym_rows: list[dict[str, Any]] = []
    try:
        op.open(panel + "/")
    except (OSError, urllib.error.URLError):
        op = None  # type: ignore[assignment]
    if op is not None:
        try:
            eb = json.loads(
                op.open(
                    urllib.request.Request(
                        panel + "/api/analysis/entry-blocks",
                        headers={"Origin": panel},
                    )
                ).read().decode()
            )
            eb_rows = list(eb.get("rows") or [])
        except (OSError, json.JSONDecodeError, urllib.error.URLError):
            pass
        try:
            sym_payload = json.loads(
                op.open(
                    urllib.request.Request(
                        panel + "/api/symbols",
                        headers={"Origin": panel},
                    )
                ).read().decode()
            )
            sym_rows = list(sym_payload.get("symbols") or [])
        except (OSError, json.JSONDecodeError, urllib.error.URLError):
            pass
    fills = fill_focus(eb_rows)
    geometry = book_trail_geometry(sym_rows)
    give_back = give_back_post_restart(post_rows)
    prem_all = premature_sl_metrics(rows)
    prem_post_m = premature_sl_metrics(post_rows) if post_rows else premature_sl_metrics([])
    frame = unfreeze_gate_frame(n_new)
    gate = book_robust.audit_from_panel(panel)
    bad = [r for r in gate if not r.get("ok")]
    # Catastrophe at safety checkpoint (n>=25): rate pinned at 1.0 with
    # enough denom, or gate6 broken. Improvement / per-symbol floors wait n=100.
    catastrophe = False
    cat_reasons: list[str] = []
    if n_new >= int(frame["safety_at"]):
        if bad:
            catastrophe = True
            cat_reasons.append("gate6")
        post_rate = prem_post_m.get("rate")
        post_den = int(prem_post_m.get("sl_denom") or 0)
        if post_rate is not None and post_den >= 5 and float(post_rate) >= 0.999:
            catastrophe = True
            cat_reasons.append("premature_rate_1.0")
    safety_ok = (
        n_new >= int(frame["safety_at"])
        and not catastrophe
        and not bad
    )
    evidence_ok = (
        n_new >= int(frame["evidence_at"])
        and safety_ok
        and (prem_post_m.get("lift") is not None)
    )
    rep = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "frozen": frozen(),
        "baseline": {
            "new_trades": bl.get("new_trades"),
            "target": bl.get("target"),
            "autopsy_n": bl.get("autopsy_n"),
            "suppressed": bl.get("suppressed"),
            "restart_at": bl.get("restart_at"),
        },
        "gate_frame": frame,
        "premature_sl": prem,
        "premature_total": int(sum(prem.values())),
        "premature_sl_post_restart": prem_post,
        "premature_total_post_restart": int(sum(prem_post.values())),
        "premature_metrics": prem_all,
        "premature_metrics_post_restart": prem_post_m,
        "give_back_post_restart": give_back,
        "trail_geometry": geometry,
        "fill": fills,
        "gate6": {
            "ok_all": not bad,
            "bad": [r.get("symbol") for r in bad],
            "rows": [
                {"symbol": r.get("symbol"), "wins": r.get("wins"),
                 "floor": r.get("floor"), "sum_r": r.get("sum_r"), "ok": r.get("ok")}
                for r in gate
            ],
        },
        "catastrophe": catastrophe,
        "catastrophe_reasons": cat_reasons,
        "safety_checkpoint_ok": safety_ok,
        "evidence_gate_ok": evidence_ok,
        # Legacy hint = safety checkpoint (not evidence of improvement).
        "unfreeze_ready_hint": bool(
            frozen()
            and safety_ok
        ),
    }
    path = out_path if out_path is not None else OUT_PATH
    _save(path, rep)
    return rep


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Unfreeze-prep metrics snapshot")
    p.add_argument("--panel", default=PANEL)
    args = p.parse_args()
    rep = snapshot(panel=args.panel)
    print(json.dumps({
        "new": (rep.get("baseline") or {}).get("new_trades"),
        "target": (rep.get("baseline") or {}).get("target"),
        "phase": (rep.get("gate_frame") or {}).get("phase"),
        "premature_total": rep.get("premature_total"),
        "premature_post": rep.get("premature_total_post_restart"),
        "premature_rate_post": (rep.get("premature_metrics_post_restart") or {}).get("rate"),
        "premature_lift_post": (rep.get("premature_metrics_post_restart") or {}).get("lift"),
        "gate6_ok": (rep.get("gate6") or {}).get("ok_all"),
        "safety_ok": rep.get("safety_checkpoint_ok"),
        "evidence_ok": rep.get("evidence_gate_ok"),
        "unfreeze_ready_hint": rep.get("unfreeze_ready_hint"),
        "fill": rep.get("fill"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())