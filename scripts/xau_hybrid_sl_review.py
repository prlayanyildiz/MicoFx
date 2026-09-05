"""XAU hybrid SL review — report-only (Claude 04:35 escalate path).

Scans ``sl_atr_mult`` challengers with charged holdout + 6-slice
``upgrade_robust`` + premature autopsy count. Never lands while the exec
pipeline is frozen (and has no apply path by default).
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import urllib.request
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from micofx.bar_snapshot import read, snapshot_path
from micofx.holdout_cost import charged_holdout
from micofx.models import SymbolConfig
from micofx.mt5client import timeframe_seconds
from micofx.optimizer import premature_sl_count_from_autopsy
from scripts.exec_gates import (
    charged_slice_nets,
    pipeline_frozen,
    slice_wins,
    upgrade_robust,
)
from scripts.session_exec import live_trade_sessions

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
DEFAULT_SYMBOL = "XAUUSD"
SL_CANDIDATES: tuple[float, ...] = (0.5, 0.7, 0.8, 1.0)
MIN_PREMATURE = 5


def _fetch_json(path: str, panel: str = PANEL) -> dict[str, Any]:
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    return json.loads(
        op.open(
            urllib.request.Request(panel + path, headers={"Origin": panel})
        ).read().decode()
    )


def load_symbol_row(symbol: str = DEFAULT_SYMBOL, panel: str = PANEL) -> dict[str, Any]:
    body = _fetch_json("/api/symbols", panel)
    for row in body.get("symbols") or []:
        if str(row.get("symbol") or "") == symbol:
            return dict(row)
    raise KeyError(symbol)


def score_sl(
    row: dict[str, Any],
    vals: tuple[float, ...] = SL_CANDIDATES,
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
    for val in vals:
        overlay = deepcopy(row)
        for k in ("available", "digits", "description"):
            overlay.pop(k, None)
        overlay["sl_atr_mult"] = float(val)
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


def review_sl(
    row: dict[str, Any],
    *,
    autopsy_rows: list[dict[str, Any]] | None = None,
    vals: tuple[float, ...] = SL_CANDIDATES,
) -> dict[str, Any]:
    """Build a gate table. Recommendation never implies an auto land."""
    sym = str(row.get("symbol") or DEFAULT_SYMBOL)
    try:
        live_sl = float(row.get("sl_atr_mult") or 0.0)
    except (TypeError, ValueError):
        live_sl = 0.0
    scored = score_sl(row, vals)
    live_nets = charged_slice_nets(row)
    live_hold = None
    for sl, hold in scored.items():
        if abs(float(sl) - live_sl) < 1e-9 and isinstance(hold, dict):
            live_hold = hold
            break
    premature = 0
    if autopsy_rows is not None:
        premature = premature_sl_count_from_autopsy(autopsy_rows, sym)

    candidates: list[dict[str, Any]] = []
    for sl in vals:
        hold = scored.get(float(sl))
        nets = charged_slice_nets(row, field="sl_atr_mult", value=float(sl))
        row_out: dict[str, Any] = {
            "sl": float(sl),
            "live": abs(float(sl) - live_sl) < 1e-9,
            "net_r": None,
            "pf": None,
            "trades": None,
            "wins": None,
            "sum_r": None,
            "nets": None,
            "upgrade_ok": False,
            "note": "score yok",
        }
        if isinstance(hold, dict):
            try:
                row_out["net_r"] = round(float(hold.get("net_r") or 0.0), 1)
                row_out["pf"] = round(float(hold.get("profit_factor") or 0.0), 2)
                row_out["trades"] = hold.get("trades")
            except (TypeError, ValueError):
                pass
            row_out["note"] = "ok"
        if nets is not None:
            row_out["nets"] = [round(n, 1) for n in nets]
            row_out["wins"] = slice_wins(nets)
            row_out["sum_r"] = round(sum(nets), 1)
            if not row_out["live"]:
                row_out["upgrade_ok"] = upgrade_robust(live_nets, nets)
                if not row_out["upgrade_ok"]:
                    row_out["note"] = "upgrade_robust False"
            else:
                row_out["note"] = "live"
        candidates.append(row_out)

    gated = [c for c in candidates if c.get("upgrade_ok")]
    # Prefer last-seg among gated; else none.
    best = None
    if gated:
        best = max(
            gated,
            key=lambda c: (
                float(c.get("net_r") or -1e18),
                float(c.get("sum_r") or -1e18),
            ),
        )

    return {
        "symbol": sym,
        "live_sl": live_sl,
        "frozen": pipeline_frozen(),
        "premature_n": premature,
        "premature_ok": premature >= MIN_PREMATURE,
        "min_premature": MIN_PREMATURE,
        "candidates": candidates,
        "best_gated": best,
        "live_last_seg": (
            None if live_hold is None
            else round(float(live_hold.get("net_r") or 0.0), 1)
        ),
        "land_allowed": False,  # explicit: this module never lands
        "verdict": _verdict(live_sl, best, premature, pipeline_frozen()),
    }


def _verdict(
    live_sl: float,
    best: dict[str, Any] | None,
    premature: int,
    frozen: bool,
) -> str:
    if frozen:
        base = "FROZEN — land yok"
    else:
        base = "land yolu kapali (review-only modul)"
    if best is None:
        return f"{base}; keep sl={live_sl:g} (hicbir challenger upgrade_robust gecmedi)"
    if premature < MIN_PREMATURE:
        return (
            f"{base}; en iyi gated sl={best['sl']:g} ama premature "
            f"{premature}<{MIN_PREMATURE} — hybrid force-SL kapali; keep {live_sl:g}"
        )
    return (
        f"{base}; gated aday sl={best['sl']:g} + premature OK — "
        f"manuel Claude review sonrasi dusunulur (otomatik land yok)"
    )


def markdown_table(report: dict[str, Any]) -> str:
    lines = [
        f"**{report.get('symbol')}** live sl={report.get('live_sl')} | "
        f"premature={report.get('premature_n')}/"
        f"{report.get('min_premature')} | frozen={report.get('frozen')}",
        "",
        "| sl | last-seg | PF | n | 6-slice | sumR | gate |",
        "|----|----------|----|---|---------|------|------|",
    ]
    for c in report.get("candidates") or []:
        wins = c.get("wins")
        sum_r = c.get("sum_r")
        net = c.get("net_r")
        pf = c.get("pf")
        mark = " **live**" if c.get("live") else ""
        gate = (
            "live" if c.get("live")
            else ("OK" if c.get("upgrade_ok") else "refuse")
        )
        lines.append(
            f"| {c['sl']:g}{mark} | "
            f"{'-' if net is None else f'{net:+.1f}'} | "
            f"{'-' if pf is None else pf} | "
            f"{c.get('trades') or '-'} | "
            f"{'-' if wins is None else f'{wins}/6'} | "
            f"{'-' if sum_r is None else f'{sum_r:+.1f}'} | "
            f"{gate} |"
        )
    lines.extend(["", f"Verdict: {report.get('verdict')}"])
    return "\n".join(lines)


def post_review_to_bridge(
    report: dict[str, Any],
    *,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    lines: list[str] = []
    wake = wake_path if wake_path is not None else (ROOT / ".bridge" / "WAKE.txt")
    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    inbox = cursor_inbox if cursor_inbox is not None else (
        ROOT / "cursor" / "FOR_CLAUDE.md")
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        block = (
            f"# Cursor -> Claude -- {ts} -- XAU hybrid SL REVIEW "
            f"(report-only)\n\n"
            f"{markdown_table(report)}\n\n"
            "MICO MOLA yok.\n"
        )
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.write_text(block + "\n---\n\n" + prev, encoding="utf-8")
        lines.append(f"inbox -> {inbox.name}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    return lines


def run(
    panel: str = PANEL,
    *,
    symbol: str = DEFAULT_SYMBOL,
    alert: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    row = load_symbol_row(symbol, panel)
    auto = _fetch_json("/api/analysis/trade-autopsies", panel)
    report = review_sl(row, autopsy_rows=list(auto.get("rows") or []))
    notes: list[str] = []
    if alert:
        notes = post_review_to_bridge(report)
    return report, notes


def main() -> int:
    p = argparse.ArgumentParser(description="XAU hybrid SL review (no land)")
    p.add_argument("--panel", default=PANEL)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    p.add_argument("--alert", action="store_true")
    args = p.parse_args()
    report, notes = run(args.panel, symbol=args.symbol, alert=args.alert)
    print(markdown_table(report), flush=True)
    for n in notes:
        print(n, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
