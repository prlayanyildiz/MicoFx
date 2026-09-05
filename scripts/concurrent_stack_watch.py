"""Concurrent per-symbol ticket alarm — Claude 20:04.

Live rule is one ticket per name (can_open cap=1 since 45decd0). This monitor
only wakes when that rule is violated. Report-only; never writes config.
"""
from __future__ import annotations

import http.cookiejar
import json
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
STATE_PATH = ROOT / ".bridge" / "CONCURRENT_STACK_STATE.json"


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


def counts_by_symbol(positions: list[dict[str, Any]]) -> dict[str, int]:
    """Count open tickets per config name (prefer config_symbol)."""
    c: Counter[str] = Counter()
    for p in positions or []:
        name = str(p.get("config_symbol") or p.get("symbol") or "").strip()
        if name:
            c[name] += 1
    return dict(c)


def evaluate(counts: dict[str, int]) -> dict[str, Any]:
    offenders = {k: int(v) for k, v in counts.items() if int(v) > 1}
    mx = max((int(v) for v in counts.values()), default=0)
    return {
        "counts": {k: int(v) for k, v in counts.items()},
        "offenders": offenders,
        "max_concurrent": mx,
        "fire": bool(offenders),
    }


def snapshot_from_positions(positions: list[dict[str, Any]]) -> dict[str, Any]:
    return evaluate(counts_by_symbol(positions))


def fetch_positions(panel: str = PANEL) -> list[dict[str, Any]]:
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/state",
                headers={"Origin": panel},
            )
        ).read().decode()
    )
    pos = body.get("positions") or []
    return list(pos) if isinstance(pos, list) else []


def snapshot(panel: str = PANEL) -> dict[str, Any]:
    return snapshot_from_positions(fetch_positions(panel))


def _ts(row: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        v = row.get(key)
        if v is None or v == "":
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def max_concurrent_from_autopsy(
    rows: list[dict[str, Any]],
    *,
    last_n: int = 25,
) -> dict[str, Any]:
    """Max overlapping open intervals per symbol on the newest last_n closes."""
    closed = [r for r in (rows or []) if _ts(r, "exit_time", "close_time")]
    closed.sort(key=lambda r: _ts(r, "exit_time", "close_time") or 0.0)
    slice_rows = closed[-int(last_n):] if last_n > 0 else closed
    by_sym: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in slice_rows:
        sym = str(r.get("symbol") or "").strip()
        fill = _ts(r, "fill_time", "open_time")
        exit_t = _ts(r, "exit_time", "close_time")
        if not sym or fill is None or exit_t is None or exit_t < fill:
            continue
        by_sym[sym].append((fill, exit_t))
    per: dict[str, int] = {}
    for sym, intervals in by_sym.items():
        events: list[tuple[float, int]] = []
        for a, b in intervals:
            events.append((a, 1))
            events.append((b, -1))
        events.sort(key=lambda x: (x[0], x[1]))
        cur = 0
        mx = 0
        for _, d in events:
            cur += d
            if cur > mx:
                mx = cur
        per[sym] = mx
    book_max = max(per.values(), default=0)
    return {
        "last_n": len(slice_rows),
        "by_symbol": per,
        "book_max": book_max,
    }


def maybe_alert(
    snap: dict[str, Any] | None = None,
    *,
    panel: str = PANEL,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    """Wake once while any name holds >1 ticket; clear latch when back to 1."""
    path = state_path if state_path is not None else STATE_PATH
    rep = snap if snap is not None else snapshot(panel)
    state = _load(path)
    lines: list[str] = []
    if not rep.get("fire"):
        if state.get("alerted") or state.get("offenders"):
            state["alerted"] = False
            state["cleared_at"] = datetime.now().isoformat(timespec="seconds")
            state["offenders"] = {}
            state["max_concurrent"] = int(rep.get("max_concurrent") or 0)
            _save(path, state)
        return []
    if state.get("alerted"):
        # Still stacked — keep state fresh but do not re-wake.
        state["counts"] = rep.get("counts") or {}
        state["offenders"] = rep.get("offenders") or {}
        state["max_concurrent"] = int(rep.get("max_concurrent") or 0)
        state["last_seen_at"] = datetime.now().isoformat(timespec="seconds")
        _save(path, state)
        return []

    wake = wake_path if wake_path is not None else (ROOT / ".bridge" / "WAKE.txt")
    inbox = cursor_inbox if cursor_inbox is not None else (
        ROOT / "cursor" / "FOR_CLAUDE.md")
    offenders = rep.get("offenders") or {}
    detail = ", ".join(f"{k}={v}" for k, v in sorted(offenders.items()))
    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE concurrent stack\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = (
        f"# Cursor -> Claude -- {ts} -- CONCURRENT STACK ALARM ({detail}).\n\n"
        "Live rule is 1 ticket/name (`can_open` cap=1). This is a silent-expected "
        "monitor — fire means the gate was bypassed or the book desynced. "
        "Config dokunma; investigate tickets.\n\n"
        "MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_text(
            body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"stack alert -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    state.update({
        "alerted": True,
        "alerted_at": datetime.now().isoformat(timespec="seconds"),
        "counts": rep.get("counts") or {},
        "offenders": offenders,
        "max_concurrent": int(rep.get("max_concurrent") or 0),
    })
    _save(path, state)
    print("AGENT_LOOP_WAKE_concurrent_stack", flush=True)
    return lines
