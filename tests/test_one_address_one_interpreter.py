"""One panel address, one interpreter — no matter how many files name them.

Two constants are written out by hand all over this project:

  * ``http://127.0.0.1:8900`` — 28 ops scripts under ``scripts/`` each declare
    their own ``PANEL = ...``, and six launchers name the port;
  * ``C:\\MicoFX-venv\\Scripts\\python.exe`` — eight launchers name the
    interpreter, which AGENTS.md calls the only one this project may use.

The obvious fix is to import them from one module. It was tried and measured:
``micofx`` is not installed into the venv, so it is importable only when the
repo root is on ``sys.path``. The documented way to run these tools is
``C:\\MicoFX-venv\\Scripts\\python.exe scripts/foo.py``, which puts
``scripts/`` on the path and not the root - the import broke 23 of the 28. The
scripts are deliberately single-file and stdlib-only so they can be run by
path; coupling them to the package to save one line each makes them harder to
run, not easier.

So the copies stay and this file makes them unable to disagree. That is the
thing that actually matters: not that the address appears once, but that there
is exactly one address. ``micofx.paths`` is where it is declared; everything
below is checked against it.

Nothing here parses code. A literal is a literal, and a mismatch is a
mismatch.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.paths import DEFAULTS_PATH, PANEL, WEB_HOST, WEB_PORT

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = sorted((ROOT / "scripts").glob("*.py"))

# Every launcher that names the interpreter or the port. Listed rather than
# globbed: a new launcher should have to be added here on purpose.
LAUNCHERS = (
    "KUR.ps1",
    "restart.bat",
    "stop.bat",
    "start_console.bat",
    "start_silent.vbs",
    "TEMIZLE_PYTHON.bat",
    "scripts/micofx.ps1",
    "scripts/start_baseline_watch.ps1",
    "scripts/start_bridge_daemon.ps1",
)

VENV_DIR = r"C:\MicoFX-venv"
INTERPRETERS = (
    rf"{VENV_DIR}\Scripts\python.exe",
    rf"{VENV_DIR}\Scripts\pythonw.exe",
)

PANEL_LITERAL = re.compile(r'PANEL\s*=\s*"([^"]+)"')
_PORT = re.compile(r"\b8900\b")
# Any drive-rooted path ending in python.exe / pythonw.exe. Spaces are allowed
# on purpose: the interpreter this project must NOT use lives at
# ``C:\Program Files\Python312\python.exe``, so a pattern that stopped at
# whitespace missed precisely the one case worth catching. The first draft of
# this file did exactly that, and pointing stop.bat at Python312 did not fail
# it - which is why the drift check below is itself checked.
_PY_EXE = re.compile(r"[A-Za-z]:\\[^\"'\r\n]*?python[w]?\.exe", re.I)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


# ------------------------------------------------------------- the address

def test_every_ops_script_dials_the_same_panel():
    wrong: list[str] = []
    for path in SCRIPTS:
        for found in PANEL_LITERAL.findall(path.read_text(encoding="utf-8",
                                                          errors="replace")):
            if found != PANEL:
                wrong.append(f"{path.name}: {found}")
    assert not wrong, (
        f"panel adresi {PANEL} ile uyusmuyor (micofx.paths.PANEL tek kaynak): "
        f"{wrong}")


def test_the_scripts_actually_carry_it():
    """Guard the guard: if the literal is ever renamed, the check above passes
    by finding nothing at all."""
    carriers = [p.name for p in SCRIPTS
                if PANEL_LITERAL.search(p.read_text(encoding="utf-8",
                                                    errors="replace"))]
    assert len(carriers) >= 20, (
        f"yalnizca {len(carriers)} script PANEL tanimliyor - literal adi mi "
        f"degisti? Kontrol hicbir seyi kapsamiyor olabilir.")


def test_the_shipped_config_binds_the_address_the_scripts_dial():
    """defaults.json is what the server binds; PANEL is what the tools call.
    They are two files, so they can disagree - and then every script quietly
    talks to a port nothing is listening on."""
    cfg = json.loads(DEFAULTS_PATH.read_text(encoding="utf-8-sig"))
    assert cfg["web_host"] == WEB_HOST, cfg["web_host"]
    assert int(cfg["web_port"]) == WEB_PORT, cfg["web_port"]


def test_the_launchers_name_the_same_port():
    """A launcher that watched the wrong port would report the app down while
    it runs, or free while it holds the socket."""
    for rel in LAUNCHERS:
        text = _read(rel)
        for found in re.findall(r"\b\d{4,5}\b", text):
            if found.startswith("89") and int(found) != WEB_PORT:
                raise AssertionError(f"{rel}: {found} != {WEB_PORT}")
        if _PORT.search(text):
            assert str(WEB_PORT) in text


# --------------------------------------------------------- the interpreter

def test_no_launcher_names_another_interpreter():
    """AGENTS.md: "Python is C:\\MicoFX-venv\\Scripts\\python.exe. No other
    interpreter." Two other FX projects on this machine run the base
    Python312 install, so a launcher that drifted onto it would be running
    this bot on somebody else's environment.
    """
    wrong: list[str] = []
    for rel in LAUNCHERS:
        for found in _PY_EXE.findall(_read(rel)):
            if found.lower() not in (i.lower() for i in INTERPRETERS):
                wrong.append(f"{rel}: {found}")
    assert not wrong, f"venv disi yorumlayici: {wrong}"


def test_the_venv_directory_is_spelled_one_way():
    """``C:\\MicoFX-venv`` vs ``C:\\MicoFx-venv`` resolves the same on Windows
    and differently everywhere else, including in a string comparison - which
    is how gece_restart's sweep decides whether a worker is ours."""
    wrong: list[str] = []
    for rel in LAUNCHERS:
        for found in re.findall(r"[A-Za-z]:\\Mico[^\\\"'\s]*-venv", _read(rel)):
            if found != VENV_DIR:
                wrong.append(f"{rel}: {found}")
    assert not wrong, f"venv klasoru farkli yazilmis: {wrong}"
