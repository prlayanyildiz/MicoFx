"""MicoFx auto-pilot — one tick: audit, fix, research, bridge.

Fully automatic income + R&D loop entry point. Safe to run from Task Scheduler
or start_income_loop.ps1 every 15 minutes.

Usage:
    C:\\MicoFX-venv\\Scripts\\python.exe scripts/auto_pilot.py
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
LOG_DIR = ROOT / "logs"
BRIDGE = ROOT / "cursor" / "FOR_CLAUDE.md"
AUTOPILOT_BEGIN = "<!-- autopilot:begin -->"
AUTOPILOT_END = "<!-- autopilot:end -->"


def _run(script: str, *args: str) -> tuple[int, str]:
    cmd = [PYTHON, str(ROOT / "scripts" / script), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(ROOT))
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out[-4000:]
    except subprocess.TimeoutExpired:
        return 1, f"{script} timeout"
    except OSError as exc:
        return 1, str(exc)


def _write_bridge(body: str) -> None:
    """Replace only the autopilot section; never wipe Cursor↔Claude brief.

    Also mirrors the tick to cursor/AUTO_PILOT.md so the brief file is not
    the only dump target.
    """
    BRIDGE.parent.mkdir(parents=True, exist_ok=True)
    mirror = BRIDGE.parent / "AUTO_PILOT.md"
    mirror.write_text(body, encoding="utf-8")
    block = f"{AUTOPILOT_BEGIN}\n{body.rstrip()}\n{AUTOPILOT_END}\n"
    existing = ""
    if BRIDGE.exists():
        existing = BRIDGE.read_text(encoding="utf-8")
    if AUTOPILOT_BEGIN in existing:
        head = existing.split(AUTOPILOT_BEGIN, 1)[0].rstrip()
        text = f"{head}\n\n{block}" if head else block
    elif existing.strip():
        # Keep whatever was there (task board, ack, etc.) — never full replace.
        text = f"{existing.rstrip()}\n\n{block}"
    else:
        text = block
    BRIDGE.write_text(text, encoding="utf-8")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sections: list[str] = [f"# Auto-pilot {ts}", ""]

    code, out = _run("income_dev_loop.py", "--auto")
    sections.append("## Gelir dongusu")
    sections.append(f"- exit: {code}")
    sections.append("```")
    sections.append(out.strip()[-2500:] or "(bos)")
    sections.append("```")
    sections.append("")

    rcode, rout = _run("research_scanner.py")
    sections.append("## AR-GE taramasi")
    sections.append(f"- exit: {rcode}")
    sections.append("- detay: `logs/research_latest.md`, `cursor/RESEARCH_QUEUE.md`")
    if rout.strip():
        sections.append("```")
        sections.append(rout.strip()[-1200:])
        sections.append("```")

    body = "\n".join(sections) + "\n"
    _write_bridge(body)

    pilot_log = LOG_DIR / "auto_pilot.log"
    with pilot_log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n{'=' * 50}\n")
        fh.write(body)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(body)
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
