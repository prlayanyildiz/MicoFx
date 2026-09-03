"""Operator-facing launcher is one command with known subcommands."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts" / "micofx.ps1"
BAT = ROOT / "MICOFX.bat"


def test_micofx_launcher_files_exist():
    assert BAT.is_file()
    assert PS1.is_file()
    text = PS1.read_text(encoding="utf-8")
    for cmd in ("install", "start", "stop", "restart", "sync", "bridge", "console"):
        assert cmd in text, cmd


def test_retired_income_loop_scripts_are_gone():
    assert not (ROOT / "GELIR_DONGUSU.bat").exists()
    assert not (ROOT / "scripts" / "start_income_loop.ps1").exists()
