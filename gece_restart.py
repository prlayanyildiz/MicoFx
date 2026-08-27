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

After the port is up, asks the live process (GET / cookie, then POST
/api/holdout/capture) to pin holdout bars through its own MT5 client. This
script never calls initialize() - a second bind would drop the trading
process. Capture failure is visible here and does not fail the restart: the
bot is already up.
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHONW = Path(r"C:\MicoFX-venv\Scripts\pythonw.exe")
LOG = ROOT / "logs" / "gece_restart.log"
PORT = 8900
BOOT_WAIT_SEC = 45
RETRIES = 2
PANEL = f"http://127.0.0.1:{PORT}"
MT5_WAIT_SEC = 60
CAPTURE_TIMEOUT_SEC = 300


def interpreter_images(executable: str) -> list[str]:
    """Paths a Windows venv worker may show as WMI ExecutablePath.

    ``sys.executable`` is the venv Scripts launcher. ProcessPool children
    report the base install (``Python312\\pythonw.exe``). Matching only the
    launcher left the 26.08 12:32 pool alive through the 00:00 restart.
    """
    seen: list[str] = []

    def add(path: str) -> None:
        raw = (path or "").strip()
        if not raw:
            return
        abs_path = os.path.abspath(raw)
        folder, name = os.path.split(abs_path)
        variants = [abs_path]
        low = name.lower()
        if low == "pythonw.exe":
            variants.append(os.path.join(folder, "python.exe"))
        elif low == "python.exe":
            variants.append(os.path.join(folder, "pythonw.exe"))
        for item in variants:
            if item not in seen:
                seen.append(item)

    add(executable)
    add(getattr(sys, "_base_executable", "") or "")
    cfg = Path(os.path.abspath(executable)).parent.parent / "pyvenv.cfg"
    if cfg.is_file():
        try:
            text = cfg.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        for line in text.splitlines():
            key, _, value = line.partition("=")
            if key.strip().lower() == "home" and value.strip():
                add(os.path.join(value.strip(), "python.exe"))
                add(os.path.join(value.strip(), "pythonw.exe"))
                break
    return seen


def cleanup_orphan_workers(executable: str | None = None) -> None:
    """Kill leftover optimizer pool children whose parent is already gone.

    Best-effort: any failure here must never block a boot or a night restart.
    """
    try:
        images = interpreter_images(executable or sys.executable)
        quoted = ",".join("'" + p.replace("'", "''") + "'" for p in images)
        script = (
            "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' or Name='python.exe'\" "
            f"| Where-Object {{ ($_.CommandLine -like '*--multiprocessing-fork*' "
            f"-or $_.CommandLine -like '*spawn_main*') "
            f"-and @({quoted}) -contains $_.ExecutablePath "
            f"-and -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue) }} "
            "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=15, check=False,
        )
        if result.returncode:
            err = (result.stderr or result.stdout or b"").decode(
                "utf-8", errors="replace").strip().replace("\n", " ")[:240]
            say(f"yetim supurge powershell rc={result.returncode} {err}")
            # Boot path (run.py) never reads gece_restart.log. Same line on
            # the live ring/disk so a parse miss cannot hide for six months.
            try:
                from micofx.logbus import LOG
                LOG.emit(
                    f"yetim supurge powershell rc={result.returncode} {err}",
                    "WARN")
            except Exception:
                pass
    except Exception:
        pass


def note_in_flight_search(opener, base: str) -> None:
    """Record a running search before this script kills the process tree.

    Midnight restart is still unconditional. 26.08 12:32 ran 11h27m and
    died with no OPT/gece line; this is the missing sentence.
    """
    try:
        with opener.open(base + "/api/state", timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        say(f"opt durumu okunamadi ({type(exc).__name__}: {exc})")
        return
    opt = data.get("opt") if isinstance(data, dict) else None
    if not isinstance(opt, dict):
        say("opt durumu okunamadi")
        return
    if not opt.get("busy"):
        say("calisan arama yok")
        return
    current = opt.get("current") or "?"
    done = opt.get("combo_done")
    total = opt.get("combo_total")
    say(f"Optimizasyon yari da kesiliyor: {current} {done}/{total}")


def _note_search_if_up(base: str) -> None:
    try:
        note_in_flight_search(panel_session(base), base)
    except Exception as exc:
        say(f"opt durumu okunamadi ({type(exc).__name__}: {exc})")


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


def panel_session(base: str):
    """Cookie from GET /. The panel rejects /api without it."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.open(base + "/", timeout=15)
    return opener


def wait_mt5_connected(opener, base: str, seconds: int = MT5_WAIT_SEC) -> bool:
    deadline = time.time() + seconds
    last = ""
    while time.time() < deadline:
        try:
            with opener.open(base + "/api/state", timeout=10) as resp:
                data = json.loads(resp.read())
            if (data.get("mt5") or {}).get("connected"):
                return True
            last = "mt5.connected=false"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                json.JSONDecodeError, OSError) as exc:
            last = f"{type(exc).__name__}"
        time.sleep(2)
    say(f"MT5 beklenirken son durum: {last}")
    return False


def request_holdout_capture(opener, base: str) -> None:
    # Capture is on the CSRF origin list. The session cookie alone is 403.
    origin = base.rstrip("/")
    req = urllib.request.Request(
        base + "/api/holdout/capture", data=b"{}", method="POST",
        headers={"Content-Type": "application/json", "Origin": origin},
    )
    with opener.open(req, timeout=CAPTURE_TIMEOUT_SEC) as resp:
        body = json.loads(resp.read())
    results = body.get("results") or []
    fails = [row for row in results if not row.get("ok")]
    say(f"holdout capture: {int(body.get('captured') or 0)} yazildi"
        + (f", atlanan {len(fails)}" if fails else ""))
    for row in fails:
        say(f"HATA holdout {row.get('symbol')}: {row.get('error')}")


def _pin_holdout_after_boot(base: str) -> None:
    """Best-effort. Restart already succeeded if we got here."""
    try:
        opener = panel_session(base)
        if not wait_mt5_connected(opener, base):
            say("HATA: bot ayakta ama MT5 baglanmadi - holdout capture atlandi")
            return
        request_holdout_capture(opener, base)
    except Exception as exc:
        say(f"HATA: holdout capture basarisiz ({type(exc).__name__}: {exc})")


def main() -> int:
    say("--- gece restart basliyor ---")
    pid = port_owner()
    if pid:
        _note_search_if_up(PANEL)
        say(f"calisan bot bulundu (port {PORT} pid {pid}) - agac durduruluyor")
        stop_tree(pid)
        time.sleep(6)
        cleanup_orphan_workers(str(PYTHONW))
    else:
        say(f"port {PORT} zaten bos - bot calismiyordu")

    for attempt in range(1, RETRIES + 1):
        start()
        for _ in range(BOOT_WAIT_SEC):
            time.sleep(1)
            if port_open():
                say(f"bot ayakta, port {PORT} dinliyor (deneme {attempt})")
                _pin_holdout_after_boot(PANEL)
                say("--- tamamlandi ---")
                return 0
        say(f"deneme {attempt}: {BOOT_WAIT_SEC} sn icinde port acilmadi")

    say(f"HATA: bot {RETRIES} denemede ayaga kalkmadi - ELLE KONTROL EDIN")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
