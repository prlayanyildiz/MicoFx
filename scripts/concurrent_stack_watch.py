"""Concurrent per-symbol ticket alarm.

Fires only when open tickets for a name exceed that symbol's live
``max_positions`` (1..5). Legal scale-ins are not breaches. Report-only.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:            # run-by-path needs the repo root
    sys.path.insert(0, str(ROOT))
# Imported under this module's own name: it is the seam callers and
# tests patch, and renaming it silently removed that seam.
from scripts.panel_session import opener as _panel_opener  # noqa: E402

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


def _clip_cap(raw: Any) -> int:
    try:
        n = int(raw or 1)
    except (TypeError, ValueError):
        n = 1
    return max(1, min(5, n))


def evaluate(
    counts: dict[str, int],
    caps: dict[str, int] | None = None,
) -> dict[str, Any]:
    """``fire`` when count > per-symbol max_positions (default cap 5 if unknown)."""
    caps = caps or {}
    offenders: dict[str, int] = {}
    for k, v in counts.items():
        limit = _clip_cap(caps[k]) if k in caps else 5
        if int(v) > limit:
            offenders[k] = int(v)
    mx = max((int(v) for v in counts.values()), default=0)
    return {
        "counts": {k: int(v) for k, v in counts.items()},
        "caps": {k: _clip_cap(caps[k]) for k in counts if k in caps},
        "offenders": offenders,
        "max_concurrent": mx,
        "fire": bool(offenders),
    }


def snapshot_from_positions(
    positions: list[dict[str, Any]],
    caps: dict[str, int] | None = None,
) -> dict[str, Any]:
    return evaluate(counts_by_symbol(positions), caps)


def fetch_positions(panel: str = PANEL) -> list[dict[str, Any]]:
    op = _panel_opener(panel)
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


def fetch_max_positions(panel: str = PANEL) -> dict[str, int]:
    op = _panel_opener(panel)
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/symbols",
                headers={"Origin": panel},
            )
        ).read().decode()
    )
    rows = body.get("symbols") if isinstance(body, dict) else None
    out: dict[str, int] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or "")
        if not sym:
            continue
        out[sym] = _clip_cap(row.get("max_positions"))
    return out


def snapshot(panel: str = PANEL) -> dict[str, Any]:
    return snapshot_from_positions(fetch_positions(panel), fetch_max_positions(panel))


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
    report: dict[str, Any],
    *,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    lines: list[str] = []
    path = state_path if state_path is not None else STATE_PATH
    state = _load(path)
    rep = report or {}
    if not rep.get("fire"):
        if state.get("alerted"):
            state = {
                "alerted": False,
                "cleared_at": datetime.now().isoformat(timespec="seconds"),
                "counts": rep.get("counts") or {},
            }
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
    caps = rep.get("caps") or {}
    detail = ", ".join(
        f"{k}={v}/{caps.get(k, '?')}" for k, v in sorted(offenders.items()))
    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE concurrent stack\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = (
        f"# Cursor -> Claude -- {ts} -- CONCURRENT STACK ALARM ({detail}).\n\n"
        "Fire = open tickets exceed that symbol's live ``max_positions`` "
        "(1..5). Legal scale-ins are OK. Config dokunma; investigate tickets.\n\n"
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
