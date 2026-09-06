"""channel_break path watch — signal fired but no fill (Claude 09:35 next).

Report-only. Silence@90 with 0 signals = regime/quiet. Once GER40/US30
produce *session* entry-block signals and still open 0, wake for gate/path
review (not a config apply).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".bridge" / "CHANNEL_BREAK_PATH.json"
PANEL = "http://127.0.0.1:8900"
SYMBOLS = ("GER40", "US30")
SESSION_H_LO = 8
SESSION_H_HI = 11
# Fire once a symbol shows this many *new* session signals with 0 opens.
MIN_SIGNALS = 1


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


def fetch_rows(
    panel: str = PANEL,
    *,
    symbols: tuple[str, ...] = SYMBOLS,
) -> dict[str, dict[str, Any]]:
    import http.cookiejar

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
    out: dict[str, dict[str, Any]] = {s: {} for s in symbols}
    for row in body.get("rows") or []:
        sym = str(row.get("symbol") or "")
        if sym in out:
            out[sym] = dict(row)
    return out


def ensure_stamp(
    raw: dict[str, dict[str, Any]],
    *,
    in_window: bool,
    day: str,
    state_path: Path | None = None,
) -> dict[str, dict[str, int]]:
    """Stamp absolute signals/opened; return per-symbol session deltas."""
    path = state_path if state_path is not None else STATE_PATH
    state = _load(path)
    if not in_window:
        return {s: {"signals": 0, "opened": 0} for s in SYMBOLS}
    stamped_day = str(state.get("stamp_day") or "")
    base = state.get("stamp") or {}
    if stamped_day != day or not isinstance(base, dict):
        stamp = {
            s: {
                "signals": int((raw.get(s) or {}).get("signals") or 0),
                "opened": int((raw.get(s) or {}).get("opened") or 0),
            }
            for s in SYMBOLS
        }
        state["stamp_day"] = day
        state["stamp"] = stamp
        state["stamped_at"] = datetime.now().isoformat(timespec="seconds")
        _save(path, state)
        return {s: {"signals": 0, "opened": 0} for s in SYMBOLS}
    out: dict[str, dict[str, int]] = {}
    for s in SYMBOLS:
        b = base.get(s) or {}
        r = raw.get(s) or {}
        out[s] = {
            "signals": max(0, int(r.get("signals") or 0) - int(b.get("signals") or 0)),
            "opened": max(0, int(r.get("opened") or 0) - int(b.get("opened") or 0)),
        }
    return out


def evaluate(
    *,
    broker_h: int | None,
    deltas: dict[str, dict[str, int]] | None = None,
    rows: dict[str, dict[str, Any]] | None = None,
    min_signals: int = MIN_SIGNALS,
) -> dict[str, Any]:
    """Fire when any symbol has session signals and still 0 opens."""
    in_window = (
        broker_h is not None
        and SESSION_H_LO <= int(broker_h) <= SESSION_H_HI
    )
    deltas = deltas or {}
    rows = rows or {}
    hits: list[dict[str, Any]] = []
    for s in SYMBOLS:
        d = deltas.get(s) or {}
        sig = int(d.get("signals") or 0)
        op = int(d.get("opened") or 0)
        if sig >= int(min_signals) and op == 0:
            row = rows.get(s) or {}
            blocks = row.get("blocks") if isinstance(row.get("blocks"), dict) else {}
            hits.append({
                "symbol": s,
                "signals": sig,
                "opened": op,
                "blocks": dict(blocks or {}),
                "lean": (
                    "path-bug smell (signal, no blocks, no open)"
                    if not blocks
                    else f"gated no-fill (blocks={dict(blocks)})"
                ),
            })
    return {
        "in_window": in_window,
        "deltas": {s: dict(deltas.get(s) or {}) for s in SYMBOLS},
        "hits": hits,
        "fire": bool(in_window and hits),
        "min_signals": int(min_signals),
    }


def snapshot(
    panel: str = PANEL,
    *,
    broker_h: int | None = None,
    state_path: Path | None = None,
    min_signals: int = MIN_SIGNALS,
) -> dict[str, Any]:
    from scripts.session_open_silence import broker_hm, session_day_key

    bh = broker_h
    if bh is None:
        bh, _ = broker_hm(panel)
    try:
        raw = fetch_rows(panel)
    except (OSError, json.JSONDecodeError, urllib.error.URLError):
        raw = {s: {} for s in SYMBOLS}
    in_window = (
        bh is not None and SESSION_H_LO <= int(bh) <= SESSION_H_HI
    )
    day = session_day_key(bh)
    deltas = ensure_stamp(
        raw, in_window=in_window, day=day, state_path=state_path)
    return evaluate(
        broker_h=bh, deltas=deltas, rows=raw, min_signals=min_signals)


def maybe_alert(
    report: dict[str, Any],
    *,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    if not report.get("fire"):
        return []
    path = state_path if state_path is not None else STATE_PATH
    state = _load(path)
    day = datetime.now().strftime("%Y-%m-%d")
    if state.get("alerted_day") == day:
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
    hits = report.get("hits") or []
    body = (
        f"# Cursor -> Claude -- {ts} -- CHANNEL_BREAK PATH: "
        f"session signal(s) but 0 opens (your 09:35 next control).\n\n"
        f"hits={hits}\ndeltas={report.get('deltas')}\n\n"
        "Silence was regime/quiet; this is signal-without-fill. "
        "Review gate/path — not a config apply. Exec FROZEN stays.\n"
        "MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_text(
            body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"cb_path -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    state["alerted_day"] = day
    state["alerted_at"] = datetime.now().isoformat(timespec="seconds")
    state["last"] = {
        "hits": hits,
        "deltas": report.get("deltas"),
        "fire": True,
    }
    _save(path, state)
    print("AGENT_LOOP_WAKE_channel_break_path", flush=True)
    return lines