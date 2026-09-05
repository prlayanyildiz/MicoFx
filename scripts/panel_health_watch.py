"""Panel reachability — one-shot wake when 8900 dies (report-only)."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".bridge" / "PANEL_DOWN_STATE.json"
PANEL = "http://127.0.0.1:8900"


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


def panel_ok(panel: str = PANEL, *, timeout: float = 5.0) -> bool:
    try:
        urllib.request.urlopen(panel + "/", timeout=timeout)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def maybe_alert(
    *,
    ok: bool | None = None,
    panel: str = PANEL,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    """Wake once while panel is down; clear the latch when it recovers."""
    path = state_path if state_path is not None else STATE_PATH
    up = panel_ok(panel) if ok is None else bool(ok)
    state = _load(path)
    if up:
        if state.get("down") or state.get("alerted"):
            state["down"] = False
            state["alerted"] = False
            state["recovered_at"] = datetime.now().isoformat(timespec="seconds")
            _save(path, state)
        return []
    if state.get("alerted") and state.get("down"):
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
    body = (
        f"# Cursor -> Claude -- {ts} -- PANEL DOWN ({panel}).\n\n"
        "Baseline watcher cannot reach live API. BTC/MT5 may still hold tickets. "
        "Recover with venv `python -u run.py` (open tickets OK for reattach). "
        "Config dokunma.\n"
        "MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_text(
            body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"panel_down -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    state.update({
        "down": True,
        "alerted": True,
        "alerted_at": datetime.now().isoformat(timespec="seconds"),
        "panel": panel,
        "ts": time.time(),
    })
    _save(path, state)
    print("AGENT_LOOP_WAKE_panel_down", flush=True)
    return lines
