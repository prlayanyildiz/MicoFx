"""Land-vs-live runtime mtime watch — Claude 20:32.

Compares ``micofx/**/*.py`` disk mtimes to the boot manifest written by
``Engine._stamp_runtime_boot``. scripts/ are excluded (separate processes,
fresh on each call). Silent = healthy. Report-only wake; restart arm flag
is written **only when the book is flat** — never mid-trade.
"""
from __future__ import annotations

import http.cookiejar
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
BOOT_PATH = ROOT / ".bridge" / "RUNTIME_BOOT_MANIFEST.json"
STATE_PATH = ROOT / ".bridge" / "STALE_RUNTIME_STATE.json"
RESTART_FLAG = ROOT / ".bridge" / "STALE_RUNTIME_RESTART_WHEN_FLAT"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def collect_manifest(root: Path | None = None) -> dict[str, float]:
    """mtimes for motor-runtime modules only (micofx/**/*.py, no __pycache__)."""
    base = root if root is not None else ROOT
    micofx = base / "micofx"
    out: dict[str, float] = {}
    if not micofx.is_dir():
        return out
    for path in micofx.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        try:
            rel = path.relative_to(base).as_posix()
            out[rel] = float(path.stat().st_mtime)
        except OSError:
            continue
    return out


def write_boot_stamp(
    root: Path | None = None,
    path: Path | None = None,
    *,
    started_at: float | None = None,
) -> dict[str, Any]:
    """Persist boot epoch + manifest (engine calls this; tests may call too)."""
    base = root if root is not None else ROOT
    out = path if path is not None else (base / ".bridge" / "RUNTIME_BOOT_MANIFEST.json")
    started = float(started_at if started_at is not None else time.time())
    payload = {
        "engine_started_at": started,
        "manifest": collect_manifest(base),
        "written_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save(out, payload)
    return payload


def load_boot(path: Path | None = None) -> dict[str, Any] | None:
    data = _load(path if path is not None else BOOT_PATH)
    if not data or not isinstance(data.get("manifest"), dict):
        return None
    return data


def evaluate(
    *,
    boot: dict[str, Any] | None,
    current: dict[str, float],
) -> dict[str, Any]:
    """Compare disk mtimes to boot manifest. Not armed → never fires."""
    if not boot or not isinstance(boot.get("manifest"), dict):
        return {
            "armed": False,
            "fire": False,
            "stale": [],
            "engine_started_at": None,
            "n_modules": len(current),
        }
    base_man = {str(k): float(v) for k, v in boot["manifest"].items()
                if isinstance(v, (int, float))}
    stale: list[dict[str, Any]] = []
    now = time.time()
    started = boot.get("engine_started_at")
    try:
        started_f = float(started) if started is not None else None
    except (TypeError, ValueError):
        started_f = None
    for rel, mtime in sorted(current.items()):
        prev = base_man.get(rel)
        if prev is None or float(mtime) > float(prev) + 1e-6:
            if prev is None:
                hours_newer = (
                    max(0.0, (float(mtime) - started_f) / 3600.0)
                    if started_f is not None
                    else 0.0
                )
                reason = "new_file"
            else:
                hours_newer = max(0.0, (float(mtime) - float(prev)) / 3600.0)
                reason = "newer_than_boot"
            stale_for_h = (
                max(0.0, (now - float(mtime)) / 3600.0)
                if float(mtime) <= now
                else 0.0
            )
            stale.append({
                "path": rel,
                "boot_mtime": prev,
                "disk_mtime": float(mtime),
                "hours_newer": round(hours_newer, 3),
                "stale_for_h": round(stale_for_h, 3),
                "reason": reason,
            })
    return {
        "armed": True,
        "fire": bool(stale),
        "stale": stale,
        "engine_started_at": started_f,
        "n_modules": len(current),
    }


def _session(panel: str = PANEL):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    return op


def fetch_n_open(panel: str = PANEL) -> int:
    op = _session(panel)
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/state", headers={"Origin": panel})
        ).read().decode()
    )
    return len(body.get("positions") or [])


def snapshot(
    *,
    root: Path | None = None,
    boot_path: Path | None = None,
) -> dict[str, Any]:
    base = root if root is not None else ROOT
    boot = load_boot(boot_path if boot_path is not None else (
        base / ".bridge" / "RUNTIME_BOOT_MANIFEST.json"))
    return evaluate(boot=boot, current=collect_manifest(base))


def maybe_alert(
    snap: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
    boot_path: Path | None = None,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
    restart_flag: Path | None = None,
    n_open: int | None = None,
    panel: str = PANEL,
) -> list[str]:
    """Wake once while disk is ahead of boot. Restart flag only when flat."""
    base = root if root is not None else ROOT
    path = state_path if state_path is not None else STATE_PATH
    rep = snap if snap is not None else snapshot(root=base, boot_path=boot_path)
    state = _load(path)
    lines: list[str] = []

    if not rep.get("armed"):
        return []

    if not rep.get("fire"):
        if state.get("alerted") or state.get("stale"):
            state["alerted"] = False
            state["cleared_at"] = datetime.now().isoformat(timespec="seconds")
            state["stale"] = []
            _save(path, state)
        # Clear a leftover restart arm if healthy again.
        flag = restart_flag if restart_flag is not None else RESTART_FLAG
        if flag.is_file():
            try:
                flag.unlink()
            except OSError:
                pass
        return []

    if state.get("alerted"):
        state["stale"] = rep.get("stale") or []
        state["last_seen_at"] = datetime.now().isoformat(timespec="seconds")
        _save(path, state)
        return []

    open_n = n_open
    if open_n is None:
        try:
            open_n = fetch_n_open(panel)
        except Exception:
            open_n = -1

    wake = wake_path if wake_path is not None else (base / ".bridge" / "WAKE.txt")
    inbox = cursor_inbox if cursor_inbox is not None else (
        base / "cursor" / "FOR_CLAUDE.md")
    stale = rep.get("stale") or []
    detail = ", ".join(
        f"{s.get('path')}(+{s.get('hours_newer')}h)" for s in stale[:6])
    if len(stale) > 6:
        detail += f" +{len(stale) - 6} more"

    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE stale runtime\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")

    flat = open_n == 0
    flag = restart_flag if restart_flag is not None else RESTART_FLAG
    restart_note = (
        "Book FLAT — restart arm flag yazildi; land edilmis kod canliya "
        "girsin diye restart uygun."
        if flat else
        f"Book OPEN ({open_n}) — restart YOK; ilk flat'te arm. "
        "Mid-trade restart yasak."
    )
    if flat:
        try:
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text(
                "stale runtime: restart when flat (armed by watch)\n"
                f"detail={detail}\n"
                f"at={datetime.now().isoformat(timespec='seconds')}\n",
                encoding="utf-8",
            )
            lines.append(f"restart flag -> {flag}")
        except OSError as exc:
            lines.append(f"restart flag fail: {exc}")
    elif flag.is_file():
        # Do not keep a stale arm while tickets are open.
        try:
            flag.unlink()
        except OSError:
            pass

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = (
        f"# Cursor -> Claude -- {ts} -- STALE RUNTIME ALARM ({detail}).\n\n"
        "Land etti ama canli degil: micofx/*.py disk mtime > boot manifest. "
        "scripts/ haric. Sessiz=saglikli monitor — fire = land→canli gecikme.\n\n"
        f"{restart_note}\n\n"
        "Config dokunma; eksenler kapali. MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_text(
            body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"stale alert -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")

    state.update({
        "alerted": True,
        "alerted_at": datetime.now().isoformat(timespec="seconds"),
        "stale": stale,
        "n_open": open_n,
        "restart_armed": bool(flat),
    })
    _save(path, state)
    print("AGENT_LOOP_WAKE_stale_runtime", flush=True)
    return lines
