"""The startup orphan sweep kills processes, so it must only reach its own.

``cleanup_orphan_workers`` runs once at boot and force-kills leftover optimizer
pool children from a previous instance. Its WMI filter named two things: the
process name (``python.exe``/``pythonw.exe``) and ``--multiprocessing-fork`` on
the command line, plus a check that the parent is gone. Nothing in that
describes MicoFx - it describes every orphaned Python multiprocessing worker on
the machine. On a box running anything else in Python, a boot here reached past
this application entirely.

A multiprocessing-fork child's command line carries no script path (it is
``spawn_main(parent_pid=..., pipe_handle=...)``), so the executable is what
identifies it. MicoFx runs from its own venv, and a worker started by that
venv's interpreter is one of ours.

Strictly narrowing: the added clause can only ever exclude processes, never
include one the old filter missed. The parent-alive check is deliberately left
as it was - PID reuse makes it MISS an orphan rather than kill a live process,
which is the safe direction for a best-effort sweep that must never block
startup.

Guarding the built command rather than the kill: running it would kill real
processes, and the defect was in what the string selected, not in how it was
executed.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run as run_module


def _captured_script(monkeypatch) -> str:
    seen: dict[str, list] = {}

    def _fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(run_module.subprocess, "run", _fake_run)
    run_module.cleanup_orphan_workers()
    assert "cmd" in seen, "powershell hic cagrilmadi"
    return seen["cmd"][-1]


# ------------------------------------------------------------- the defect

def test_the_sweep_is_scoped_to_this_interpreter(monkeypatch):
    script = _captured_script(monkeypatch)
    exe = str(Path(sys.executable).resolve())
    assert "ExecutablePath" in script, (
        "filtre yalnizca surec adina bakiyor - makinedeki her Python "
        "multiprocessing isciisini kapsiyor")
    assert exe.lower() in script.lower()


def test_a_quote_in_the_path_cannot_break_out_of_the_filter(monkeypatch):
    """A single quote would end the PowerShell string early; doubling escapes
    it. Contrived on Windows, but the sweep runs Stop-Process -Force."""
    monkeypatch.setattr(run_module.sys, "executable", r"C:\o'brien\pythonw.exe")
    script = _captured_script(monkeypatch)
    assert "o''brien" in script


# --------------------------------------------------- what must keep working

def test_it_still_only_targets_multiprocessing_children(monkeypatch):
    script = _captured_script(monkeypatch)
    assert "--multiprocessing-fork" in script


def test_it_still_only_targets_parentless_processes(monkeypatch):
    """The orphan test itself - a worker whose pool is still alive must live."""
    script = _captured_script(monkeypatch)
    assert "ParentProcessId" in script
    assert "-not (Get-Process" in script


def test_it_still_refuses_to_block_startup(monkeypatch):
    """Best-effort: any failure here must be swallowed, or a boot fails over
    housekeeping."""
    def _boom(*a, **k):
        raise OSError("powershell yok")

    monkeypatch.setattr(run_module.subprocess, "run", _boom)
    run_module.cleanup_orphan_workers()      # must not raise


def test_it_is_bounded_in_time(monkeypatch):
    """A hung powershell must not hold the boot open."""
    seen: dict[str, object] = {}

    def _fake_run(cmd, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(run_module.subprocess, "run", _fake_run)
    run_module.cleanup_orphan_workers()
    assert seen.get("timeout"), "zaman asimi yok - asili powershell acilisi kilitler"
