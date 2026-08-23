"""Nightly restart of the live bot, at the one hour nothing can be trading.

Written after 24.08: the MT5 terminal restarted itself on 22.08 at 17:19 and
the bot never reconnected. It kept running - the poll loop alive, the port
listening, diagnostics still being written - and simply stopped seeing the
market. Nothing in the log said so after the first line. The market was shut
for almost all of that, so the cost was about seventeen minutes of Monday's
open, but the same failure on a Tuesday afternoon costs a session.

Midnight is chosen because it is the only hour of the trading day when every
symbol in the book is outside its session (the earliest window opens at
01:00) and the day-end flatten has already run. A restart there cannot
interrupt a position it would otherwise be managing.

Deliberately unconditional. A health check would have to decide what "healthy"
means, and the incident this exists for looked healthy from outside: process
up, port bound, database being written. Restarting something that was fine
costs a few seconds at an hour with no trading in it. Not restarting
something that is quietly blind costs a session.

Verifies afterwards and says so either way, in its own log, because a
recovery step whose failure is silent is the thing it was written to prevent.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHONW = Path(r"C:\MicoFX-venv\Scripts\pythonw.exe")
LOG = ROOT / "logs" / "gece_restart.log"
PORT = 8900
BOOT_WAIT_SEC = 45
RETRIES = 2


def say(text: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + text
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8", errors="replace") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    stream = sys.stdout
    if stream is None:                      # pythonw: no console exists
        return
    try:
        print(line)
    except (AttributeError, ValueError, OSError):
        pass


def port_owner() -> int | None:
    """PID holding the port, or None. Uses netstat: no extra dependency."""
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                             capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        say(f"netstat okunamadi: {type(exc).__name__}")
        return None
    for row in out.splitlines():
        parts = row.split()
        if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{PORT}"):
            try:
                return int(parts[4])
            except ValueError:
                return None
    return None


def port_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2.0)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def stop_tree(pid: int) -> None:
    """Kill the whole tree. The venv launcher spawns the child that binds the
    port, so killing one PID leaves the other alive - the mistake the old
    stop.bat made before it gained /T."""
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                   capture_output=True, text=True, timeout=60)


def start() -> None:
    if not PYTHONW.is_file():
        say(f"HATA: {PYTHONW} yok - baslatilamadi")
        return
    subprocess.Popen([str(PYTHONW), "run.py"], cwd=str(ROOT),
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))


def main() -> int:
    say("--- gece restart basliyor ---")
    pid = port_owner()
    if pid:
        say(f"calisan bot bulundu (port {PORT} pid {pid}) - agac durduruluyor")
        stop_tree(pid)
        time.sleep(6)
    else:
        say(f"port {PORT} zaten bos - bot calismiyordu")

    for attempt in range(1, RETRIES + 1):
        start()
        for _ in range(BOOT_WAIT_SEC):
            time.sleep(1)
            if port_open():
                say(f"bot ayakta, port {PORT} dinliyor (deneme {attempt})")
                say("--- tamamlandi ---")
                return 0
        say(f"deneme {attempt}: {BOOT_WAIT_SEC} sn icinde port acilmadi")

    say(f"HATA: bot {RETRIES} denemede ayaga kalkmadi - ELLE KONTROL EDIN")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
