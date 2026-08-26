"""A restart must not race its own shutdown.

app.py spawns restart.bat before this process exits and says why: "restart.bat
waits for this process to release the port before relaunching". restart.bat did
not wait for anything - it slept a flat two seconds and launched.

Two seconds is usually enough, which is the problem. The shutdown ahead of it
stops the engine, closes the MT5 client and terminates the process; under load
that can run long, and when it does the new instance hits run.py's port_busy
check, prints, and exits 1. Nothing retries. The outcome is a bot completely
down with positions open, and since #043 the only trace is a line in
logs/baslatilamadi.log that nobody is watching live.

So the script now does what the comment already claimed: it polls the port and
launches once it is actually free. Bounded at thirty seconds, and it launches
anyway after that rather than giving up - a new instance refused on port_busy at
least says so, which is exactly today's behaviour, so the worst case degrades to
what it already was instead of becoming a silent no-launch.

Asserted against the script's text rather than by running it: executing this
would kill and relaunch the live application.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
RESTART = (ROOT / "restart.bat").read_text(encoding="utf-8", errors="replace")
APP = (ROOT / "micofx" / "web" / "app.py").read_text(encoding="utf-8")


# ------------------------------------------------------------- the defect

def test_it_checks_the_port_rather_than_sleeping_blind():
    assert "netstat" in RESTART and "LISTENING" in RESTART, (
        "restart.bat portu hic kontrol etmiyor - sabit bekleme, yarisi kaybederse "
        "bot acik pozisyonlarla tamamen duruyor")


def test_it_uses_the_configured_port():
    """MICO_PORT moves the app; a hardcoded 8900 would watch the wrong one and
    launch immediately every time."""
    assert "MICO_PORT" in RESTART
    assert re.search(r'set\s+"PORT=8900"', RESTART), "varsayilan port yok"


def test_the_wait_is_bounded():
    """A port held forever must not stop the relaunch attempt entirely."""
    assert re.search(r"geq\s+\d+", RESTART), "sinirsiz bekleme - hic baslamayabilir"


def test_it_launches_even_if_the_port_never_frees():
    """Worst case has to degrade to the old behaviour, not to no launch at all:
    an instance refused on port_busy reports why, a missing one says nothing."""
    stuck = RESTART[RESTART.index(":portstuck"):]
    assert "goto launch" in stuck.split(":portfree")[0]


# --------------------------------------------------- what must keep working

def test_it_still_passes_the_restart_argument():
    """Without it start_silent.vbs opens a second browser tab over the one the
    operator already has."""
    assert '"%~dp0start_silent.vbs" restart' in RESTART


def test_it_still_launches_through_the_silent_starter():
    assert "wscript.exe" in RESTART and "//B" in RESTART


def test_the_comment_in_app_py_matches_what_the_script_does():
    """The pair that drifted: the comment promised a wait the script did not
    perform. One number, two places, is the drift this codebase keeps finding -
    here it was one guarantee in two places."""
    spawn = APP[APP.index("restart.bat"):][:400]
    assert "polls until the port" in spawn or "port is actually free" in spawn
    assert "waits for this process to release the port before" not in spawn


def test_restart_cancels_a_running_search_before_mt5_dies():
    """12:32 search, 12:51 restart, no OPT iptal line, last_opt_job still running."""
    body = APP[APP.index("def app_restart"):APP.index("return app")]
    assert "optimizer.cancel()" in body
    assert body.index("optimizer.cancel()") < body.index("client.shutdown()")


def test_shutdown_cancels_too():
    body = APP[APP.index("def app_shutdown"):APP.index("def app_restart")]
    assert "optimizer.cancel()" in body
