"""MicoFX entry point: boots the MT5 bridge, trading engine and web terminal."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

# Checked here, above the imports below, rather than inside main(): micofx.web
# builds pydantic models whose annotations use ``X | None``, and pydantic v2
# resolves those at class-creation time. On 3.9 this file therefore dies with a
# TypeError from inside pydantic before a single line of ours runs, which says
# nothing about what is actually wrong.
#
# KUR.ps1 installs 3.12 when no Python is found at all, but accepts whatever it
# finds when one is present - and a server someone is deploying onto usually has
# one already. The install then "succeeds": the venv builds, pip install builds
# (numpy 1.26 supports 3.9), and the app never starts.
MIN_PYTHON = (3, 10)
if sys.version_info < MIN_PYTHON:
    raise SystemExit(
        f"MicoFX Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} veya ustunu gerektiriyor; "
        f"bulunan {sys.version.split()[0]} ({sys.executable}).\n"
        f"  Python 3.12 kurup KUR.bat'i yeniden calistirin.")

import uvicorn

from micofx import APP_NAME, __version__
from micofx.engine import Engine
from micofx.logbus import LOG
from micofx.mt5client import MT5Client
from micofx.optimizer import Optimizer
from micofx.paths import ensure_dirs, load_defaults
from micofx.store import Store
from micofx.web import create_app


def ensure_streams() -> None:
    """Give the process usable stdout/stderr even with no console attached.

    ``pythonw.exe`` - what the silent launcher uses - starts without a console,
    so CPython sets ``sys.stdout``/``sys.stderr`` to ``None``. The first
    ``print()`` below (or any write from uvicorn's logging) then dies with an
    AttributeError and the app vanishes with no trace, which is why a background
    start previously only survived when launched through a visible console.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            stream = open(os.devnull, "w", encoding="utf-8")
            setattr(sys, name, stream)
            if getattr(sys, f"__{name}__", None) is None:
                setattr(sys, f"__{name}__", stream)


def cleanup_orphan_workers() -> None:
    """Kill any leftover optimizer worker processes from a previous instance.

    The optimizer's process pool spawns ``pythonw --multiprocessing-fork``
    children; if a previous run was ended by killing only its own PID (the
    old stop.bat, before it gained ``/T``) those children survived as
    orphans - real memory sitting idle with nothing left to hand results
    back to, indistinguishable from a live pool without checking whether
    their parent still exists. This runs once at startup as a backstop for
    any launcher/crash path that still misses the tree, never during normal
    operation. Best-effort: any failure here must never block startup.
    """
    try:
        # Scoped to THIS interpreter. The filter named only the process name
        # and --multiprocessing-fork, which describes every orphaned Python
        # worker on the machine, not ours - on a box running anything else in
        # Python this reaches past MicoFx entirely. A multiprocessing-fork
        # child's command line carries no script path, so the executable is
        # what identifies it: MicoFx runs from its own venv, and a worker
        # started by that venv's interpreter is one of ours.
        #
        # Strictly narrowing - it can only ever kill fewer processes than
        # before, never more. The parent-alive check is left as it was; PID
        # reuse makes it MISS an orphan rather than kill a live process, which
        # is the safe direction for a best-effort sweep.
        exe = os.path.abspath(sys.executable).replace("'", "''")
        script = (
            "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' or Name='python.exe'\" "
            "| Where-Object { $_.CommandLine -like '*--multiprocessing-fork*' "
            f"-and $_.ExecutablePath -eq '{exe}' "
            "-and -not (Get-Process -Id $_.ParentProcessId -ErrorAction SilentlyContinue) } "
            "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=15, check=False,
        )
    except Exception:
        pass


def port_busy(host: str, port: int) -> bool:
    """True only if the port cannot be bound; a lingering socket must not block startup."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return False
        except OSError:
            return True


def main() -> int:
    ensure_streams()
    cleanup_orphan_workers()
    try:
        # Inside the same guard as load_defaults: ensure_dirs raises
        # RuntimeError for the same reason and must not be the one step that
        # still ends as a traceback.
        ensure_dirs()
        defaults = load_defaults()
    except RuntimeError as exc:
        # Same contract as the Store() guard below: a broken config must end
        # as a readable line and exit 1, not as a traceback into pythonw.exe's
        # void where the app just fails to appear.
        print(f"[{APP_NAME}] {exc}")
        return 1
    host = os.getenv("MICO_HOST", defaults.get("web_host", "127.0.0.1"))
    port = int(os.getenv("MICO_PORT", defaults.get("web_port", 8900)))

    if port_busy(host, port):
        print(f"[{APP_NAME}] {host}:{port} zaten kullanimda. Acik olan terminali kullanin "
              f"veya MICO_PORT ile baska bir port secin.")
        return 1

    try:
        store = Store()
    except RuntimeError as exc:
        # Store() already logged the sqlite detail to logs/micofx.log; this
        # path exists so a broken settings DB ends as a readable message and
        # exit code 1 instead of a traceback into pythonw.exe's void.
        print(f"[{APP_NAME}] {exc}")
        return 1
    client = MT5Client(store.system.mt5_terminal_path)

    if store.system.autostart_mt5:
        # Optional convenience: launch the *configured* terminal64.exe only if
        # it is not already running. Never bypasses the strict path lock below
        # - connect() still verifies the attached terminal matches the config.
        if client.ensure_terminal_process():
            wait_sec = max(0, int(store.system.autostart_mt5_wait_sec or 0))
            deadline = time.time() + wait_sec
            while time.time() < deadline:
                if client.connect():
                    break
                time.sleep(2.0)

    if not client.connected and not client.connect():
        LOG.emit(client.last_error or "MT5 baglantisi kurulamadi", "ERROR")

    engine = Engine(store, client)
    optimizer = Optimizer(store, client)
    engine.supervisor.optimizer = optimizer
    # Same lock the web routes (DELETE/PATCH/reset/seed) already serialise
    # against the engine's own entry path with - without it, apply()/
    # apply_secondary()'s open-position check races the exact same way those
    # routes used to before entry_lock existed.
    optimizer.entry_lock = engine.entry_lock
    # Only matters once host is not 127.0.0.1 - see create_app()'s docstring.
    api_token = os.getenv("MICO_API_TOKEN", "").strip()
    if host not in ("127.0.0.1", "localhost") and not api_token:
        # A warning alone left the real default behaviour "wide open" - the
        # whole point of a kill-switch/panic route is that it must not be
        # reachable by anyone who can merely reach the port. Auto-generate a
        # token instead of just complaining, so "exposed and reachable by
        # anyone" is never actually a state this process can end up in - only
        # "exposed and needs the token from this log line" is.
        import secrets
        api_token = secrets.token_urlsafe(24)
        # Not printed in full: the log file/console has a wider, less
        # predictable audience than "whoever loads the web UI this token is
        # meant to gate" (log shipping, wider file permissions, screen
        # sharing while debugging). The UI itself gets the real token via the
        # <meta> tag create_app() injects into the served page - that is the
        # intended channel, not the log.
        LOG.emit(
            f"MICO_HOST={host} ile disari aciliyorsunuz ama MICO_API_TOKEN ayarli degil - "
            f"rastgele bir token uretildi ve otomatik uygulandi (...{api_token[-6:]} ile bitiyor, "
            f"web panelinden erisilebilir). Kalici olmasi icin MICO_API_TOKEN ortam "
            f"degiskenine yazin, yoksa her baslatmada degisir.", "ERROR")
    app = create_app(store, client, engine, optimizer, api_token=api_token)

    # The observation loop always runs so the terminal shows live state; order
    # placement always waits for an explicit start. ``system.running`` is
    # still persisted (so the UI/API can show whether trading was on when the
    # process went down), but it must never be read back to auto-resume
    # trading itself - a crash or a killed process is exactly the moment a
    # human should look before orders start going out again, not the moment
    # to silently pick back up. Only the explicit, user-set ``autostart_bot``
    # flag may start the bot on its own.
    engine.start_watch()
    if store.system.autostart_bot:
        threading.Timer(3.0, engine.start).start()

    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"
    # The token gate now covers "/" itself (see create_app()'s docstring), so
    # a bare GET here 401s - the auto-opened tab needs the token in the query
    # string to actually land on the page. Printed line stays token-free
    # (same log-audience reasoning as the ERROR line above); this is a local
    # process action, not something that gets written anywhere.
    open_url = f"{url}/?token={api_token}" if api_token else url
    print(f"[{APP_NAME} {__version__}] terminal: {url}")
    if os.getenv("MICO_OPEN_BROWSER", "1") == "1" and defaults.get("open_browser", True):
        threading.Timer(1.2, lambda: webbrowser.open(open_url)).start()

    try:
        uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
    except KeyboardInterrupt:
        pass
    finally:
        engine.shutdown()
        client.shutdown()
        store.close()
        time.sleep(0.2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
