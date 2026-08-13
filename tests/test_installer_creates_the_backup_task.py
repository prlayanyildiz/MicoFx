"""Everything says the nightly backup runs. Nothing was creating it.

Three separate places describe the evening backup as a thing that happens.
README: "backup.py her aksam Windows Gorev Zamanlayici ile calisir", and then
instructions for changing that task's properties. models.py, beside
``backup_enabled``: "The Windows task still fires; it is backup.py that reads
this and exits without writing". The panel ships the master switch on.

No code in the repository created the task. Not KUR.ps1, not anything else -
there was no schtasks or Register-ScheduledTask call anywhere. And
docs/KURULUM.md, the guide for setting this up on a blank Windows machine from
scratch, did not mention the backup at all. So a machine installed by following
the documentation end to end had no backup task, while every document said it
had one. The task on the development machine exists because someone made it by
hand.

The cost lands on the one file that cannot be recovered from anywhere else.
data/micofx.db is gitignored, and it holds every symbol config, every
optimisation result and everything the supervisor has learned - README says so
itself: "GitHub kodu tutar, bunlarin hicbirini tutmaz."

Installed Interactive, which is how README already describes it running: no
elevation, works on the lock screen, skips a night when the session is fully
logged out. Idempotent, and a failure warns loudly with the command to run by
hand rather than taking the install down - the application runs fine without
backups, but passing over it silently would break the same promise a second
time.

Asserted against the script's text: running KUR.ps1 rebuilds a venv and
registers a scheduled task on this machine.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
KUR = (ROOT / "KUR.ps1").read_text(encoding="utf-8-sig", errors="replace")
README = (ROOT / "README.md").read_text(encoding="utf-8", errors="replace")
KURULUM = (ROOT / "docs" / "KURULUM.md").read_text(encoding="utf-8-sig", errors="replace")

TASK = "MicoFX Aksam Yedegi"


# ------------------------------------------------------------- the defect

def test_the_installer_creates_the_task():
    assert "schtasks /create" in KUR, (
        "kurulum yedek gorevini kurmuyor - README calistigini soyluyor")
    assert TASK in KUR


def test_it_uses_the_name_the_docs_tell_people_to_look_for():
    """README sends the operator to Task Scheduler by this exact name."""
    assert TASK in README
    assert TASK in KUR


def test_it_runs_backup_py_with_the_installed_interpreter():
    block = KUR[KUR.index("$TaskName"):]
    assert "backup.py" in block
    assert "$Venv" in block or "$VenvPy" in block, (
        "sistem python'u ile kurarsa venv bagimliliklari olmadan calisir")


def test_the_from_scratch_guide_mentions_it():
    """The guide is for a blank machine; a backup nobody knows to check is the
    same as no backup."""
    assert "Yedek" in KURULUM and "schtasks" in KURULUM


# --------------------------------------------------- it must not make install worse

def test_it_does_not_recreate_an_existing_task():
    block = KUR[KUR.index("$TaskName"):]
    assert "schtasks /query" in block, "her kurulumda gorevi yeniden yaratir"
    assert "Zaten var" in block


def test_a_failure_warns_instead_of_failing_the_install():
    """The app runs without backups; a dead install helps nobody."""
    block = KUR[KUR.index("$TaskName"):]
    assert "OTOMATIK ALINMAYACAK" in block, "sessizce gecerse soz ikinci kez bosa cikar"
    assert "throw" not in block, "yedek gorevi kurulumu dusurmemeli"


def test_it_launches_without_a_console_window():
    """A console popping up at 22:00 every night on a trading machine."""
    block = KUR[KUR.index("$TaskName"):]
    assert "pythonw.exe" in block


def test_it_has_a_daily_schedule_and_a_time():
    block = KUR[KUR.index("$TaskName"):]
    assert "/sc daily" in block
    assert re.search(r"/st\s+\d\d:\d\d", block)


def test_the_hour_it_schedules_is_the_hour_the_guide_promises():
    """The time is written down in three places and drifted on the first try.

    KUR.ps1 registered 23:30 while the machine every document was written
    against runs at 22:00 - so the guide told an operator to expect a backup at
    an hour their machine would never fire. Nothing here picks which hour is
    right; it only refuses to let the three copies disagree, which is the way
    this went wrong.
    """
    scheduled = re.search(r"/st\s+(\d\d:\d\d)", KUR[KUR.index("$TaskName"):]).group(1)
    hh, mm = scheduled.split(":")
    # KURULUM.md writes it the Turkish way: "22:00'de", "23:30'da".
    assert re.search(rf"{hh}:{mm}'[dt]", KURULUM), (
        f"KUR.ps1 {scheduled}'da kuruyor, kurulum kilavuzu baska saat soyluyor")
    # The installer echoes the hour back to whoever is watching it install.
    assert scheduled in KUR[KUR.index("Kuruldu"):KUR.index("Kuruldu") + 60]
