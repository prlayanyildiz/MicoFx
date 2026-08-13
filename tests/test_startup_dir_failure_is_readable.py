"""Every startup step must fail as a line, not as a traceback into the void.

The rule is stated twice already, in paths.load_defaults and in Store.__init__:
a startup problem ends as something an operator can act on and exit code 1,
because under pythonw.exe - which start_silent.vbs uses - an unhandled traceback
goes to a stream nobody reads and the app simply never appears.

ensure_dirs sat between those two and did not hold it. It ran outside any
try/except in run.py, and both things it does can raise OSError: mkdir against a
read-only volume, a denied path, or a file already occupying the directory's
name; rename when the source is locked, which antivirus and file sync both do
routinely on Windows.

Store.__init__ calls it too, and run.py catches only RuntimeError from Store, so
an OSError escaped through that route as well. Raising RuntimeError at the
source closes both.

Not reproduced as a live failure: the legacy files do not exist on this install
and the directories are writable. What is demonstrable is the shape - a
permission error now produces a readable message and main() returns 1, where it
previously propagated. That matters most on a machine being deployed to, where
the install path may not be writable and there is no console to read.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import paths


# ------------------------------------------------------------- the defect

def test_an_unwritable_directory_raises_something_readable(monkeypatch):
    def _denied(self, *a, **k):
        raise PermissionError(13, "Erisim reddedildi", str(self))

    monkeypatch.setattr(Path, "mkdir", _denied)
    with pytest.raises(RuntimeError) as err:
        paths.ensure_dirs()
    text = str(err.value)
    assert "yazma izni" in text, f"eyleme donusmeyen mesaj: {text}"
    assert "Erisim reddedildi" in text, "altta yatan hata gizlenmis"


def test_a_locked_legacy_file_raises_something_readable(monkeypatch, tmp_path):
    old, new = tmp_path / "micoai.log", tmp_path / "micofx.log"
    old.write_text("gecmis", encoding="utf-8")
    monkeypatch.setattr(paths, "_LEGACY", [(old, new)])
    monkeypatch.setattr(Path, "rename",
                        lambda self, target: (_ for _ in ()).throw(
                            PermissionError(13, "Dosya kullanimda", str(self))))
    with pytest.raises(RuntimeError) as err:
        paths.ensure_dirs()
    text = str(err.value)
    assert "kilitli" in text
    assert str(old) in text and str(new) in text, "hangi dosya oldugu yazmiyor"


def test_main_returns_one_instead_of_propagating(monkeypatch):
    """The whole point of the RuntimeError: run.py already has a handler that
    prints and exits 1, and ensure_dirs now reaches it."""
    import run

    monkeypatch.setattr(run, "ensure_streams", lambda: None)
    monkeypatch.setattr(run, "cleanup_orphan_workers", lambda: None)
    monkeypatch.setattr(run, "ensure_dirs",
                        lambda: (_ for _ in ()).throw(RuntimeError("klasor yok")))
    assert run.main() == 1


# --------------------------------------------------- what must keep working

def test_it_creates_the_directories_normally(monkeypatch, tmp_path):
    made: list[Path] = []
    real = Path.mkdir

    def _spy(self, *a, **k):
        made.append(self)
        return real(self, *a, **k)

    monkeypatch.setattr(paths, "CONFIG_DIR", tmp_path / "config")
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(paths, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(paths, "_LEGACY", [])
    monkeypatch.setattr(Path, "mkdir", _spy)
    paths.ensure_dirs()
    assert {p.name for p in made} == {"config", "data", "logs"}


def test_a_legacy_file_is_still_carried_over(monkeypatch, tmp_path):
    old, new = tmp_path / "micoai.db", tmp_path / "micofx.db"
    old.write_text("gecmis", encoding="utf-8")
    monkeypatch.setattr(paths, "_LEGACY", [(old, new)])
    paths.ensure_dirs()
    assert new.read_text(encoding="utf-8") == "gecmis"
    assert not old.exists()


def test_an_existing_target_is_not_overwritten(monkeypatch, tmp_path):
    """The guard that makes the rename safe to retry."""
    old, new = tmp_path / "micoai.db", tmp_path / "micofx.db"
    old.write_text("eski", encoding="utf-8")
    new.write_text("yeni", encoding="utf-8")
    monkeypatch.setattr(paths, "_LEGACY", [(old, new)])
    paths.ensure_dirs()
    assert new.read_text(encoding="utf-8") == "yeni"
