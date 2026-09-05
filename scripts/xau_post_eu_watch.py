"""Post-EU XAU heightened watch — alert on fresh losers (no auto-disable).

Armed when ``xau_temp_reenable`` lifts the night flag. For ``WINDOW_H`` hours,
any new XAU close with ``r_realised < 0`` wakes Claude once per ticket.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".bridge" / "XAU_POST_EU_WATCH.json"
WINDOW_H = 3


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


def _seed_tickets(
    rows: list[dict[str, Any]] | None,
    extra: list[Any] | None = None,
) -> list[str]:
    """Known XAU tickets at arm — skip even if exit_time skews past reenabled_at."""
    out: set[str] = set()
    for t in extra or []:
        if t is not None and str(t):
            out.add(str(t))
    for row in rows or []:
        if str(row.get("symbol") or "") != "XAUUSD":
            continue
        ticket = row.get("ticket")
        if ticket is None or ticket == "":
            continue
        out.add(str(ticket))
    return sorted(out)


def arm(
    *,
    autopsy_n: int | None = None,
    now_ts: float | None = None,
    seed_rows: list[dict[str, Any]] | None = None,
    seed_tickets: list[Any] | None = None,
) -> None:
    """Stamp re-enable moment (idempotent refresh).

    ``seed_rows`` / ``seed_tickets`` mark pre-arm XAU closes so clock-skewed
    ``exit_time`` values cannot false-wake (04.09 #324704274).
    """
    now = float(now_ts if now_ts is not None else time.time())
    data = _load(STATE_PATH)
    prior = {
        str(t) for t in (data.get("alerted_tickets") or []) if t is not None
    }
    seeded = set(_seed_tickets(seed_rows, seed_tickets)) | prior
    data.update({
        "reenabled_at": now,
        "reenabled_iso": datetime.now().isoformat(timespec="seconds"),
        "autopsy_n": autopsy_n,
        "alerted_tickets": sorted(seeded),
        "window_h": WINDOW_H,
    })
    _save(STATE_PATH, data)


def active(
    *,
    now_ts: float | None = None,
    state_path: Path | None = None,
) -> bool:
    path = state_path if state_path is not None else STATE_PATH
    data = _load(path)
    started = data.get("reenabled_at")
    if started is None:
        return False
    try:
        started_f = float(started)
    except (TypeError, ValueError):
        return False
    now = float(now_ts if now_ts is not None else time.time())
    window = float(data.get("window_h") or WINDOW_H)
    return 0 <= (now - started_f) < window * 3600


def maybe_alert(
    rows: list[dict[str, Any]],
    *,
    now_ts: float | None = None,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    """Wake once per new post-EU XAU loser ticket."""
    path = state_path if state_path is not None else STATE_PATH
    if not active(now_ts=now_ts, state_path=path):
        return []
    data = _load(path)
    try:
        started = float(data.get("reenabled_at") or 0)
    except (TypeError, ValueError):
        return []
    alerted = {
        str(t) for t in (data.get("alerted_tickets") or []) if t is not None
    }
    fresh: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("symbol") or "") != "XAUUSD":
            continue
        try:
            rr = float(row.get("r_realised") or 0.0)
        except (TypeError, ValueError):
            continue
        if rr >= 0:
            continue
        ts = row.get("exit_time") or row.get("fill_time")
        try:
            ts_f = float(ts)
        except (TypeError, ValueError):
            continue
        if ts_f < started:
            continue
        ticket = str(row.get("ticket") or ts_f)
        if ticket in alerted:
            continue
        fresh.append(row)
        alerted.add(ticket)
    if not fresh:
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
    bits = ", ".join(
        f"#{r.get('ticket')} R={r.get('r_realised')} ${r.get('profit')}"
        for r in fresh
    )
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = (
        f"# Cursor -> Claude -- {ts} -- POST-EU XAU loser(s): {bits}\n\n"
        f"Heightened watch ({WINDOW_H}h after re-enable). Alert-only — "
        "disable karari senin/operator. Config/SL dokunma.\n"
        "MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_text(
            body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"post_eu -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    data["alerted_tickets"] = sorted(alerted)
    data["last_alert_at"] = datetime.now().isoformat(timespec="seconds")
    _save(path, data)
    print("AGENT_LOOP_WAKE_xau_post_eu_loss", flush=True)
    return lines
