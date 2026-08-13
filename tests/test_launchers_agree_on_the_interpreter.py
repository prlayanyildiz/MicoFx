"""The three ways to start this app must not pick different interpreters.

KUR.ps1 states the policy and the reason: the virtual environment lives at
C:\\MicoFX-venv, deliberately outside the project folder, because a venv holds
an absolute reference to the python.exe of the machine that built it - so a
project-local ".venv" carried to another machine by OneDrive comes back broken
("No Python at ..."). The installer even warns when it finds one: "proje icinde
eski bir .venv duruyor, artik kullanilmiyor".

start_console.bat answered that correctly: the installed venv, and PATH if it is
missing. start_silent.vbs did not - its candidate list preferred a project-local
.venv/venv over PATH, which is to say it preferred the option the installer
declares dead and known to break under file sync, ahead of a working
interpreter.

It only bites when C:\\MicoFX-venv is absent, since the installed venv matches
first otherwise. That is exactly the situation someone is in while repairing an
install, and picking a stale project venv there produces a failure that looks
like the app rather than like the environment.

Narrowing, not widening: the silent launcher now considers fewer paths, never
more. Asserted against the scripts' text - running either starts or restarts the
live application.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
VBS = (ROOT / "start_silent.vbs").read_text(encoding="utf-8", errors="replace")
CONSOLE = (ROOT / "start_console.bat").read_text(encoding="utf-8", errors="replace")
KUR = (ROOT / "KUR.ps1").read_text(encoding="utf-8-sig", errors="replace")

INSTALLED = r"C:\MicoFX-venv"


def _candidates(vbs: str) -> str:
    start = vbs.index("candidates = Array(")
    return vbs[start:vbs.index(")", start)]


# ------------------------------------------------------------- the defect

def test_the_silent_launcher_does_not_reach_for_a_project_local_venv():
    block = _candidates(VBS)
    assert ".venv" not in block, (
        "kurulumun olu ilan ettigi proje ici venv hala aday - ve PATH'ten once")
    assert "root &" not in block, "proje klasorune gore aday kalmis"


def test_all_three_name_the_same_installed_venv():
    assert INSTALLED in _candidates(VBS)
    assert INSTALLED in CONSOLE
    assert INSTALLED.replace("\\", "\\") in KUR or "MicoFX-venv" in KUR


def test_the_installer_still_calls_a_project_venv_obsolete():
    """The source of the policy. If this warning ever goes, the narrowing above
    needs revisiting rather than silently outliving its reason."""
    assert "artik kullanilmiyor" in KUR


# --------------------------------------------------- what must keep working

def test_the_silent_launcher_still_prefers_the_console_less_interpreter():
    """pythonw before python: the whole point of this launcher is no window."""
    block = _candidates(VBS)
    assert block.index("pythonw.exe") < block.index("Scripts\\python.exe")


def test_it_still_falls_back_to_path_when_no_venv_exists():
    """Removing the project-local candidates must not remove the last resort."""
    assert 'WhereExe(shell, "pythonw.exe")' in VBS
    assert 'WhereExe(shell, "python.exe")' in VBS


def test_the_console_launcher_still_falls_back_to_path():
    assert re.search(r'set\s+"PY=python"', CONSOLE)
