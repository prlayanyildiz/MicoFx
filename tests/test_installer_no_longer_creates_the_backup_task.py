"""The installer must NOT create the nightly backup task any more.

This file replaces test_installer_creates_the_backup_task, which asserted the
opposite. Operator 10.09: "backup.py surecini bastan sona iptal edelim,
bununla alakali da surec calismasin". The ``MicoFX Aksam Yedegi`` scheduled
task is unregistered on the machine and KUR.ps1's step 5 no longer creates it.

Inverted rather than deleted, because "we removed it" is not a behaviour
anyone can check. The old step created the task AND ran it once to verify; a
reinstall would have quietly brought both back, and nothing would have failed.

What this decision costs is stated in the same places the decision is:
data/micofx.db is not in Git, so every symbol config, optimiser result and
supervisor verdict now exists in exactly one copy. backup.py stays in the tree
and still works when run by hand - nothing schedules it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
KUR = (ROOT / "KUR.ps1").read_text(encoding="utf-8", errors="replace")
TASK = "MicoFX Aksam Yedegi"


def test_the_installer_registers_no_scheduled_task_at_all():
    """Neither schtasks nor the PowerShell cmdlet, for any task."""
    assert "schtasks /create" not in KUR
    assert "schtasks /run" not in KUR
    assert "Register-ScheduledTask" not in KUR


def test_it_does_not_name_the_task_as_something_it_creates():
    """The name may appear in the note explaining the removal - it must not
    appear in a command."""
    for line in KUR.splitlines():
        if TASK in line:
            stripped = line.strip()
            assert stripped.startswith("#") or stripped.startswith("Step "), stripped


def test_the_removal_says_what_it_costs():
    """A reader deciding whether to put it back needs the reason it was there:
    micofx.db is the only copy of every config and opt result."""
    note = KUR[KUR.index("[5]"):KUR.index("[6]")]
    assert "micofx.db" in note
    assert "Git" in note


def test_backup_is_off_by_default_now():
    """A fresh install, or a settings reset, must not start writing archives
    to a path the operator did not ask for."""
    import json

    from micofx.models import SystemConfig

    assert SystemConfig().backup_enabled is False
    shipped = json.loads((ROOT / "config" / "defaults.json")
                         .read_text(encoding="utf-8-sig"))["system"]
    assert shipped["backup_enabled"] is False


def test_backup_py_is_still_there_and_still_honours_the_switch():
    """Cancelled means unscheduled, not deleted: run by hand it must still
    refuse to write while the switch is off."""
    src = (ROOT / "backup.py").read_text(encoding="utf-8")
    assert "backup_enabled" in src
    assert "Otomatik yedekleme kapali" in src
