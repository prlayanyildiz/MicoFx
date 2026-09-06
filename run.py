"""MicoFX entry point: boots the MT5 bridge, trading engine and web terminal."""
from __future__ import annotations

import os
import socket
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
    _msg = (f"MicoFX Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} veya ustunu gerektiriyor; "
            f"bulunan {sys.version.split()[0]} ({sys.executable}). "
            f"Python 3.12 kurup KUR.bat'i yeniden calistirin.")
    # Plain stdlib rather than startup_fail(): this deliberately runs above the
    # micofx imports, and on an interpreter this old some of them cannot import
    # at all. Same file, so there is only one place to look either way.
    # Skipped under pytest for the same reason startup_fail skips it: the file
    # is what an operator reads after an unexplained non-start, and test noise
    # in it defeats that.
    if "pytest" not in sys.modules:
        try:
            _d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(_d, exist_ok=True)
            with open(os.path.join(_d, "baslatilamadi.log"), "a", encoding="utf-8") as _fh:
                _fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + _msg + "\n")
        except Exception:
            pass
    raise SystemExit(_msg)

import uvicorn

from micofx import APP_NAME, __version__
from micofx.engine import Engine
from micofx.logbus import LOG
from micofx.mt5client import MT5Client
from micofx.optimizer import Optimizer
from micofx.paths import LOG_DIR, ensure_dirs, load_defaults
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


def startup_fail(message: str) -> int:
    """Report a fatal startup problem somewhere it can actually be read.

    ensure_streams above points stdout/stderr at os.devnull when there is no
    console, which is correct for its own purpose - a print() must not take the
    app down - but it also means every readable line the startup guards produce
    goes nowhere. paths.load_defaults, paths.ensure_dirs and Store.__init__ each
    raise RuntimeError specifically so a failure ends as a line an operator can
    act on; the port check and the interpreter-version guard do the same. Under
    start_silent.vbs - the normal way this runs on a server - all of it was
    written to the void, and the app simply did not appear. Which is the exact
    outcome those guards exist to prevent.

    Redirecting the streams themselves to a file was the obvious fix and is the
    wrong one: uvicorn's access logging goes to stderr too, and the panel polls
    every second or two, so that file would be thousands of lines an hour. Only
    the fatal messages come here.

    Appends, capped, and never raises: a startup already failing must not fail
    differently because the report could not be written.
    """
    print(message)
    if "pytest" in sys.modules:
        # The suite drives main() to prove this very contract, and it did so
        # into the real file: every line in logs/baslatilamadi.log was fixture
        # text - "x", "klasor yok", defaults.json paths under a scratch
        # basetemp. A diagnostic an operator reaches for after an unexplained
        # non-start is worthless if it is full of test noise, which is the one
        # thing it exists to not be.
        #
        # Guarded here rather than by asking each test to patch LOG_DIR: that
        # works only for tests that remember, and the two that exist today did
        # not. The check is on the module being loaded at all, so it cannot be
        # true in the shipped app.
        return 1
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = LOG_DIR / "baslatilamadi.log"
        if path.exists() and path.stat().st_size > 256 * 1024:
            path.unlink()
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {message}" + "\n")
    except Exception:
        pass
    return 1


def cleanup_orphan_workers() -> None:
    """Kill leftover optimizer pool children from a previous instance.

    The filter lives in gece_restart so the night restart can use it
    without importing this file (uvicorn / MT5). Same rule: parent gone,
    ``--multiprocessing-fork``, and an image that belongs to this venv
    *or* its base interpreter - the Scripts launcher path alone missed
    the 26.08 12:32 pool.
    """
    try:
        import gece_restart
        gece_restart.cleanup_orphan_workers(sys.executable)
    except Exception:
        pass


def _resweep_orphans_later() -> None:
    """Boot sweep can run while the previous process is still dying.

    27.08 05:15: new PID 6264 swept while 12372 was still alive, so the
    fourteen workers were skipped; then 12372 exited and they sat as
    orphans (~1 GB). A second cause (27.08 17:52): the PowerShell
    Where-Object closer was not an f-string, so every sweep including
    this backstop parsed as nothing. Gece and restart.bat still sweep
    after the old tree is gone.
    """
    if "pytest" in sys.modules:
        return

    def _later() -> None:
        for delay in (8.0, 45.0):
            time.sleep(delay)
            cleanup_orphan_workers()

    threading.Thread(
        target=_later, name="micofx-orphan-resweep", daemon=True,
    ).start()


def port_busy(host: str, port: int) -> bool:
    """True only if the port cannot be bound; a lingering socket must not block startup."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return False
        except OSError:
            return True


def _retry_autostart(engine) -> None:
    """Keep offering start() until IPC is up or the boot window closes.

    A one-shot Timer(3s, engine.start) fired while initialize() was still
    the 60s pipe wait; start() failed and trading never opened (02.09).
    Sleep between tries releases the GIL so the panel stays alive. Stop
    once IPC latched on this terminal boot - hammering start() buys nothing.
    """
    deadline = time.time() + 90.0
    client = engine.client
    while time.time() < deadline:
        if engine.running:
            return
        exe = getattr(client, "_exe_from_path", lambda _p: None)(
            client.terminal_path) if client.terminal_path else None
        if exe is not None and getattr(client, "_ipc_latched", lambda _e=None: False)(exe):
            return
        try:
            if engine.start().get("ok"):
                return
        except Exception:
            pass
        time.sleep(2.0)


def main() -> int:
    # Before Store() / Engine: those emit WARN/ERROR. Ad-hoc imports of
    # micofx must not reach this line, so they cannot append the live log.
    LOG.enable_disk()
    ensure_streams()
    cleanup_orphan_workers()
    _resweep_orphans_later()
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
        return startup_fail(f"[{APP_NAME}] {exc}")
    host = os.getenv("MICO_HOST", defaults.get("web_host", "127.0.0.1"))
    port = int(os.getenv("MICO_PORT", defaults.get("web_port", 8900)))

    if port_busy(host, port):
        return startup_fail(
            f"[{APP_NAME}] {host}:{port} zaten kullanimda. Acik olan terminali "
            f"kullanin veya MICO_PORT ile baska bir port secin.")

    try:
        store = Store()
    except RuntimeError as exc:
        # Store() already logged the sqlite detail to logs/micofx.log; this
        # path exists so a broken settings DB ends as a readable message and
        # exit code 1 instead of a traceback into pythonw.exe's void.
        return startup_fail(f"[{APP_NAME}] {exc}")
    client = MT5Client(store.system.mt5_terminal_path)
    client.autostart = bool(store.system.autostart_mt5)
    # initialize() holds the GIL for up to 60s (package ignores timeout=).
    # Stay False until uvicorn is accepting so GET / is served first.
    client.allow_initialize = False

    if store.system.autostart_mt5:
        # Launch only. initialize() holds the GIL for the IPC timeout, so a
        # wait loop of connect() here delayed uvicorn.bind past
        # start_silent.vbs's 2.5s browser open (02.09 reboot hang). The
        # watch loop's ensure() attaches once the pipe is up; the path lock
        # still runs there.
        client.ensure_terminal_process()

    engine = Engine(store, client)
    optimizer = Optimizer(store, client)
    engine.supervisor.optimizer = optimizer
    # Same lock the web routes (DELETE/PATCH/reset/seed) already serialise
    # against the engine's own entry path with - without it, apply()/
    # apply_secondary()'s open-position check races the exact same way those
    # routes used to before entry_lock existed.
    optimizer.entry_lock = engine.entry_lock
    from micofx.autopilot import maybe_land_pending_xau_sl
    maybe_land_pending_xau_sl(optimizer, store)
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

    # Bind first. start_watch is a thread start, not initialize(). Arm
    # initialize a moment later so GET / has a live socket; a failed IPC
    # is not retried on the same terminal boot (GIL loop).
    def _arm_initialize() -> None:
        client.allow_initialize = True

    def _watch_after_bind() -> None:
        engine.start_watch()
        threading.Timer(2.0, _arm_initialize).start()
        if store.system.autostart_bot:
            threading.Thread(
                target=_retry_autostart, args=(engine,),
                daemon=True, name="micofx-autostart",
            ).start()

    app.router.add_event_handler("startup", _watch_after_bind)

    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"
    print(f"[{APP_NAME} {__version__}] terminal: {url}")
    if os.getenv("MICO_OPEN_BROWSER", "1") == "1" and defaults.get("open_browser", True):
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

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
