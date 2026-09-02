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
    BRIDGE.parent.mkdir(parents=True, exist_ok=True)
    BRIDGE.write_text(body, encoding="utf-8")

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
