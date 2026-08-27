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
identifies it. On Windows a venv ``pythonw.exe`` is a launcher:
``sys.executable`` is the Scripts copy, WMI ``ExecutablePath`` on the
workers is the base install. Matching only the launcher misses the pool.

The parent-alive check is left as it was - PID reuse makes it MISS an
orphan rather than kill a live process, which is the safe direction for a
best-effort sweep that must never block startup.

Guarding the built command rather than the kill: running it would kill real
processes, and the defect was in what the string selected, not in how it was
executed.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gece_restart
import run as run_module


def _captured_script(monkeypatch) -> str:
    seen: dict[str, list] = {}

    def _fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(gece_restart.subprocess, "run", _fake_run)
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


def test_the_sweep_also_matches_the_venv_base_interpreter(monkeypatch):
    """Windows venv pythonw.exe is a launcher. WMI ExecutablePath on the
    workers is the base install (Python312\\pythonw.exe); sys.executable is
    the venv Scripts copy. Exact-match on sys.executable missed fourteen
    26.08 12:32 orphans (~1.2 GB) through the 00:00 gece restart.
    """
    monkeypatch.setattr(
        run_module.sys, "executable", r"C:\MicoFX-venv\Scripts\pythonw.exe")
    monkeypatch.setattr(
        sys, "_base_executable", r"C:\Program Files\Python312\pythonw.exe",
        raising=False)
    script = _captured_script(monkeypatch)
    assert r"C:\Program Files\Python312\pythonw.exe" in script, (
        "filtre yalnizca venv Scripts yoluna bakiyor - taban pythonw "
        "iscileri yetim kaliyor")
    assert r"C:\MicoFX-venv\Scripts\pythonw.exe" in script
    assert r"C:\Program Files\Python312\python.exe" in script


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
    assert "spawn_main" in script


def test_it_still_only_targets_parentless_processes(monkeypatch):
    """The orphan test itself - a worker whose pool is still alive must live."""
    script = _captured_script(monkeypatch)
    assert "ParentProcessId" in script
    assert "-not (Get-Process" in script


def test_the_where_object_scriptblock_actually_parses(monkeypatch):
    """Closing `}}` sat on a non-f-string, so PowerShell saw an extra `}`
    and rc=1. check=False swallowed it; fourteen workers survived two
    restarts. The Where-Object closer has to be an f-string too.
    """
    script = _captured_script(monkeypatch)
    assert script.count("{") == script.count("}")
    assert "SilentlyContinue) }" in script
    assert "SilentlyContinue) }}" not in script


def test_a_powershell_failure_is_logged_not_swallowed(monkeypatch, tmp_path):
    monkeypatch.setattr(gece_restart, "LOG", tmp_path / "gece_restart.log")

    def _fail(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, b"", b"Unexpected token '}'")

    monkeypatch.setattr(gece_restart.subprocess, "run", _fail)
    run_module.cleanup_orphan_workers()
    logged = (tmp_path / "gece_restart.log").read_text(encoding="utf-8")
    assert "rc=1" in logged
    assert "Unexpected token" in logged


def test_a_powershell_failure_also_reaches_the_live_log(monkeypatch, tmp_path):
    """Boot sweep failures must not live only in gece_restart.log."""
    monkeypatch.setattr(gece_restart, "LOG", tmp_path / "gece_restart.log")
    seen: list[tuple] = []

    def _emit(msg, level="INFO"):
        seen.append((msg, level))

    monkeypatch.setattr("micofx.logbus.LOG.emit", _emit)

    def _fail(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, b"", b"Unexpected token '}'")

    monkeypatch.setattr(gece_restart.subprocess, "run", _fail)
    run_module.cleanup_orphan_workers()
    assert seen, "canli loga dusmedi"
    assert seen[0][1] == "WARN"
    assert "rc=1" in seen[0][0]


def test_it_still_refuses_to_block_startup(monkeypatch):
    """Best-effort: any failure here must be swallowed, or a boot fails over
    housekeeping."""
    def _boom(*a, **k):
        raise OSError("powershell yok")

    monkeypatch.setattr(gece_restart.subprocess, "run", _boom)
    run_module.cleanup_orphan_workers()      # must not raise


def test_it_is_bounded_in_time(monkeypatch):
    """A hung powershell must not hold the boot open."""
    seen: dict[str, object] = {}

    def _fake_run(cmd, **kwargs):
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(gece_restart.subprocess, "run", _fake_run)
    run_module.cleanup_orphan_workers()
    assert seen.get("timeout"), "zaman asimi yok - asili powershell acilisi kilitler"


def test_the_boot_resweep_is_armed_and_skips_pytest():
    """05:15 race: one sweep at boot while the old parent still lived.

    A delayed pass is the backstop. It must not start a Stop-Process
    thread under pytest.
    """
    src = Path(run_module.__file__).read_text(encoding="utf-8")
    assert "_resweep_orphans_later()" in src.split("def main", 1)[1]
    assert '"pytest" in sys.modules' in src

