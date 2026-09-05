"""One-shot EU-open readiness brief (~broker h=7). Alert-only."""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".bridge" / "EU_OPEN_BRIEF_STATE.json"
PANEL = "http://127.0.0.1:8900"
BRIEF_HOUR = 7


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


def maybe_brief(
    *,
    broker_h: int | None,
    panel: str = PANEL,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
    brief_hour: int = BRIEF_HOUR,
) -> list[str]:
    """Once per calendar day when broker hour hits ``brief_hour``."""
    if broker_h is None or int(broker_h) < int(brief_hour):
        return []
    path = state_path if state_path is not None else STATE_PATH
    state = _load(path)
    day = datetime.now().strftime("%Y-%m-%d")
    if state.get("briefed_day") == day:
        return []
    # Lightweight live snapshot for the brief body.
    sym_line = "symbols: (panel okunamadi)"
    pos_line = "positions: ?"
    try:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        op.open(panel + "/")
        h = {"Origin": panel}
        st = json.loads(
            op.open(urllib.request.Request(panel + "/api/state", headers=h)
                    ).read().decode())
        syms = json.loads(
            op.open(urllib.request.Request(panel + "/api/symbols", headers=h)
                    ).read().decode()).get("symbols") or []
        bits = []
        for s in syms:
            bits.append(
                f"{s.get('symbol')}:en={s.get('enabled')} "
                f"tf={s.get('timeframe')}/{s.get('strategy')}")
        sym_line = "; ".join(bits)
        pos = st.get("positions") or []
        pos_line = (
            ", ".join(
                f"{p.get('symbol')}#{p.get('ticket')} "
                f"${p.get('profit')} mfe={p.get('mfe_r')}"
                for p in pos) or "flat")
    except Exception as exc:
        sym_line = f"panel fail: {exc}"
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
    xau_flag = (ROOT / ".bridge" / "XAU_TEMP_DISABLE_UNTIL_EU").is_file()
    frozen = (ROOT / ".bridge" / "EXEC_PIPELINE_FROZEN").is_file()
    body = (
        f"# Cursor -> Claude -- {ts} -- EU-OPEN BRIEF (broker_h={broker_h})\n\n"
        f"XAU temp-disable flag={'YES -> auto re-enable at h>=8' if xau_flag else 'no'}; "
        f"exec frozen={frozen}. Post-EU 3h watch arms on lift.\n"
        f"GER40/US30 session ~08:00. Auto-A vetoed.\n\n"
        f"Book: {pos_line}\n{sym_line}\n\n"
        "Config dokunma. MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_text(
            body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"eu_brief -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    state["briefed_day"] = day
    state["briefed_at"] = datetime.now().isoformat(timespec="seconds")
    state["broker_h"] = broker_h
    _save(path, state)
    print("AGENT_LOOP_WAKE_eu_open_brief", flush=True)
    return lines
