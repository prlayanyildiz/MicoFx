"""Baseline watch launcher must never spawn a console python.exe.

WMI Create of ``Scripts\\python.exe`` puts a visible window on the taskbar
and dies on RDP reconnect; the launcher then respawned every few seconds.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = (ROOT / "scripts" / "start_baseline_watch.ps1").read_text(
    encoding="utf-8", errors="replace"
)


def test_launcher_binds_venv_pythonw_not_python():
    assert r'C:\MicoFX-venv\Scripts\pythonw.exe' in PS1
    assert r'$Py = "C:\MicoFX-venv\Scripts\python.exe"' not in PS1


def test_launcher_waits_for_the_whole_watch_tree():
    assert "function Wait-BaselineWatchGone" in PS1
    assert "Wait-Process -Id $procId" not in PS1
