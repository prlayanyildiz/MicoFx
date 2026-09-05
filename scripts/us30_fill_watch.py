"""US30 fill vs spread after post-restart — report-only (Claude 05:20).

Tracks entry-block fill_rate / spread blocks once the US session window is
open. Never widens MSA (freeze owns that). Wakes Claude once if fill stays
poor after enough post-restart signals.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
STATE_PATH = ROOT / ".bridge" / "US30_FILL_BASELINE.json"
DEFAULT_SYMBOL = "US30"

# After this many post-restart US30 signals, poor fill is evidence.
MIN_SIGNALS = 8
# Claude 07:20: US30 closest shrink candidate — earlier trigger in session open.
SESSION_OPEN_MIN_SIGNALS = 4
POOR_FILL = 0.35  # below this with spread-dominant blocks → alert
# Pre-entry refuses — count in panel totals but not as fill-gate evidence.
SOFT_BLOCKS = frozenset({
    "seans_disi", "piyasa_kapali", "saat_kapali", "gun_kapali", "hafta_sonu",
})
_SOFT_BLOCKS = SOFT_BLOCKS  # back-compat alias


def _load(path: Path = STATE_PATH) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def arm_session_day(
    state_path: Path,
    *,
    day_key: str,
) -> bool:
    """Once per session day: clear alerted so a new open window can wake once.

    Used for NAS100 15:00 heighten — one poor-fill alert per session day.
    Returns True when the day was newly armed.
    """
    st = _load(state_path)
    if str(st.get("session_day") or "") == str(day_key):
        return False
    st["session_day"] = str(day_key)
    st["session_armed_at"] = datetime.now().isoformat(timespec="seconds")
    st["alerted"] = False
    st.pop("alerted_at", None)
    _save(st, state_path)
    return True


def fetch_us30_row(panel: str = PANEL, symbol: str = DEFAULT_SYMBOL) -> dict[str, Any]:
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/analysis/entry-blocks",
                headers={"Origin": panel},
            )
        ).read().decode()
    )
    for row in body.get("rows") or []:
        if str(row.get("symbol") or "") == symbol:
            return dict(row)
    return {}


def evaluate_row(
    row: dict[str, Any],
    *,
    min_signals: int | None = None,
) -> dict[str, Any]:
    signals = int(row.get("signals") or 0)
    opened = int(row.get("opened") or 0)
    blocks = row.get("blocks") if isinstance(row.get("blocks"), dict) else {}
    retries = row.get("retries") if isinstance(row.get("retries"), dict) else {}
    soft_n = sum(int(blocks.get(k) or 0) for k in _SOFT_BLOCKS)
    # Prefer reconstructed actionable count when blocks are present; fall back
    # to raw signals when the row has no block breakdown.
    if blocks:
        hard_blocks = sum(
            int(v) for k, v in blocks.items() if str(k) not in _SOFT_BLOCKS)
        actionable = opened + hard_blocks
    else:
        actionable = max(0, signals - soft_n)
    try:
        fill = float(row.get("fill_rate") or 0.0)
    except (TypeError, ValueError):
        fill = (opened / signals) if signals else 0.0
    action_fill = (opened / actionable) if actionable else 0.0
    spread_n = int(blocks.get("spread") or 0)
    spread_retries = int(retries.get("spread") or 0)
    hard = {k: int(v) for k, v in blocks.items() if str(k) not in _SOFT_BLOCKS}
    dominant = max(hard, key=hard.get) if hard else (
        max(blocks, key=blocks.get) if blocks else "")
    need = int(min_signals) if min_signals is not None else MIN_SIGNALS
    poor = (
        actionable >= need
        and action_fill < POOR_FILL
        and (dominant == "spread" or spread_n >= max(3, actionable // 3))
    )
    return {
        "symbol": str(row.get("symbol") or DEFAULT_SYMBOL),
        "signals": signals,
        "actionable_signals": actionable,
        "opened": opened,
        "fill_rate": round(fill, 4),
        "action_fill_rate": round(action_fill, 4),
        "spread_blocks": spread_n,
        "spread_retries": spread_retries,
        "dominant_block": dominant,
        "poor_fill": poor,
        "min_signals": need,
        "poor_fill_threshold": POOR_FILL,
    }


def snapshot(
    panel: str = PANEL,
    *,
    symbol: str = DEFAULT_SYMBOL,
    state_path: Path | None = None,
    min_signals: int | None = None,
) -> dict[str, Any]:
    path = state_path if state_path is not None else STATE_PATH
    prev = _load(path)
    row = fetch_us30_row(panel, symbol=symbol)
    rep = evaluate_row(row, min_signals=min_signals) if row else {
        "symbol": symbol,
        "signals": 0,
        "actionable_signals": 0,
        "opened": 0,
        "fill_rate": 0.0,
        "action_fill_rate": 0.0,
        "spread_blocks": 0,
        "spread_retries": 0,
        "dominant_block": "",
        "poor_fill": False,
        "min_signals": min_signals if min_signals is not None else MIN_SIGNALS,
        "poor_fill_threshold": POOR_FILL,
        "note": "no entry-block row yet",
    }
    out = {
        **{k: v for k, v in prev.items()
           if k in ("restart_at", "spread_send_recheck_test", "book_6slice",
                    "note", "alerted")},
        **rep,
        "stamped_at": datetime.now().isoformat(timespec="seconds"),
        "restart_at": prev.get("restart_at") or "2026-09-04T05:22:16",
    }
    _save(out, path)
    return out


def maybe_alert(
    report: dict[str, Any],
    *,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    if not report.get("poor_fill"):
        return []
    path = state_path if state_path is not None else STATE_PATH
    state = _load(path)
    if state.get("alerted"):
        return []
    wake = wake_path if wake_path is not None else (ROOT / ".bridge" / "WAKE.txt")
    inbox = cursor_inbox if cursor_inbox is not None else (
        ROOT / "cursor" / "FOR_CLAUDE.md")
    lines: list[str] = []
    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    sym = str(report.get("symbol") or DEFAULT_SYMBOL)
    body = (
        f"# Cursor -> Claude -- {ts} -- {sym} FILL ALERT "
        f"(post-restart spread-gate check).\n\n"
        f"signals={report.get('signals')} opened={report.get('opened')} "
        f"fill={report.get('fill_rate')} "
        f"spread_blocks={report.get('spread_blocks')} "
        f"dominant={report.get('dominant_block')}\n\n"
        "Send-time recheck should reduce fill-time widen leaks. Review before "
        "any MSA widen (exec still FROZEN).\n\n"
        "MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.write_text(body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"US30 fill alert -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    state.update(report)
    state["alerted"] = True
    state["alerted_at"] = datetime.now().isoformat(timespec="seconds")
    _save(state, path)
    return lines


def main() -> int:
    p = argparse.ArgumentParser(description="US30 fill vs spread watch")
    p.add_argument("--panel", default=PANEL)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    p.add_argument("--alert", action="store_true")
    args = p.parse_args()
    rep = snapshot(args.panel, symbol=args.symbol)
    print(
        f"{rep['symbol']} fill={rep.get('fill_rate')} "
        f"sig={rep.get('signals')} open={rep.get('opened')} "
        f"spread={rep.get('spread_blocks')} poor={rep.get('poor_fill')}",
        flush=True,
    )
    notes: list[str] = []
    if args.alert:
        notes = maybe_alert(rep)
    for n in notes:
        print(n, flush=True)
    return 1 if rep.get("poor_fill") else 0


if __name__ == "__main__":
    raise SystemExit(main())
