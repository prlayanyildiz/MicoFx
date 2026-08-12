"""The installer must refuse a Python the app cannot import on.

KUR.ps1 printed the interpreter version and never checked it. It installs 3.12
via winget when no Python is found at all, but when one IS found - the ordinary
case on a server someone is deploying onto - it proceeds with whatever that is.

The install then reports success at every step. The venv builds, pip install
builds (numpy 1.26 still supports 3.9), and the app never starts: micofx.web
declares pydantic models whose annotations use ``X | None``, pydantic v2
resolves those at class-creation time, and on 3.9 that is a TypeError raised
from inside pydantic during import - before any line of ours runs, and saying
nothing about what is actually wrong.

Nothing declared the floor anywhere. There is no pyproject or setup.py, and
requirements.txt pins libraries rather than an interpreter. So it is stated
twice, deliberately: run.py enforces it above its own imports (a launch that
bypasses KUR.bat still fails legibly) and KUR.ps1 asks the found interpreter to
check itself. Two statements of one number is the drift this codebase keeps
finding, so the last test here pins them together.

Why 3.10 and not higher: it is the lowest version the code actually imports on.
Raising it is a real decision about which machines can run this, not a detail to
bump by accident.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
RUN_PY = (ROOT / "run.py").read_text(encoding="utf-8")
KUR_PS1 = (ROOT / "KUR.ps1").read_text(encoding="utf-8-sig")


def _run_py_floor() -> tuple[int, int]:
    m = re.search(r"MIN_PYTHON\s*=\s*\((\d+),\s*(\d+)\)", RUN_PY)
    assert m, "run.py'de MIN_PYTHON bulunamadi"
    return int(m.group(1)), int(m.group(2))


def _installer_floor() -> tuple[int, int]:
    m = re.search(r"sys\.version_info\s*>=\s*\((\d+),\s*(\d+)\)", KUR_PS1)
    assert m, "KUR.ps1 bulunan Python'un surumunu hic kontrol etmiyor"
    return int(m.group(1)), int(m.group(2))


# ------------------------------------------------------------- the defect

def test_the_installer_checks_the_version_it_found():
    assert _installer_floor() == (3, 10)


def test_the_installer_stops_rather_than_carrying_on():
    """Printing a warning and continuing would still end in the venv being
    built against an interpreter the app cannot import on."""
    after = KUR_PS1[KUR_PS1.index("sys.version_info"):]
    gate = after[:after.index("# ---")] if "# ---" in after else after
    assert "exit 1" in gate, "surum kapisi kuruluma devam ediyor"


def test_run_py_enforces_it_too():
    """A launch that never goes through KUR.bat must still fail legibly."""
    assert _run_py_floor() == (3, 10)


def test_run_py_checks_before_it_imports_micofx():
    """The whole point: on an old interpreter the pydantic TypeError fires at
    import time, so a check placed after these imports never runs."""
    guard = RUN_PY.index("MIN_PYTHON")
    for mod in ("from micofx", "import uvicorn"):
        assert guard < RUN_PY.index(mod), f"surum kapisi {mod} satirindan sonra"


def test_the_message_names_the_version_it_found():
    """"Too old" without saying which interpreter is unactionable when several
    are installed - which is exactly when this fires."""
    assert "sys.executable" in RUN_PY[RUN_PY.index("MIN_PYTHON"):][:900]


# --------------------------------------------------- the two must not drift

def test_the_installer_and_the_app_agree_on_the_floor():
    assert _installer_floor() == _run_py_floor(), (
        "KUR.ps1 ile run.py farkli bir minimum soyluyor - biri kabul edip "
        "digeri reddeder")


def test_this_interpreter_satisfies_the_floor():
    """Guards the pair from being raised above what actually runs here."""
    assert sys.version_info >= _run_py_floor()
