"""The evening backup must survive having no console.

The scheduled task runs pythonw, where ``sys.stdout`` is None. ``_emit``
wrote to it unguarded, so the first operator line raised AttributeError out
of the script and the task returned 1 - twice, on 17 and 18 August, while
running the same file by hand worked and looked fine. The exit code was the
only record, so nobody looked.

These tests pin both halves of the repair: the write is guarded, and the
line reaches a log file that exists whether or not anyone is watching.
"""
from __future__ import annotations

import importlib
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

backup = importlib.import_module("backup")


def test_emit_does_not_raise_when_stdout_is_absent(tmp_path, monkeypatch):
    """pythonw's world: no stdout at all."""
    monkeypatch.setattr(backup, "LOG_FILE", tmp_path / "yedek.log")
    monkeypatch.setattr(sys, "stdout", None)
    backup._emit("yedek alindi")          # must not raise
    assert "yedek alindi" in (tmp_path / "yedek.log").read_text(encoding="utf-8")


def test_emit_does_not_raise_when_stdout_is_closed(tmp_path, monkeypatch):
    """A handle that existed and went away, e.g. a dropped redirection."""
    monkeypatch.setattr(backup, "LOG_FILE", tmp_path / "yedek.log")
    stream = io.StringIO()
    stream.close()
    monkeypatch.setattr(sys, "stdout", stream)
    backup._emit("kapali akis")
    assert "kapali akis" in (tmp_path / "yedek.log").read_text(encoding="utf-8")


def test_emit_survives_a_cp1252_console_and_still_logs(tmp_path, monkeypatch):
    """The 16.08 failure: Turkish text through a cp1252 console.

    Kept alongside the new cases because the log must carry the line even
    when the console can only take a mangled version of it.
    """
    monkeypatch.setattr(backup, "LOG_FILE", tmp_path / "yedek.log")

    class Cp1252Stream(io.StringIO):
        encoding = "cp1252"

        def write(self, text: str) -> int:
            text.encode("cp1252")          # raises on 'ğ'
            return super().write(text)

    monkeypatch.setattr(sys, "stdout", Cp1252Stream())
    backup._emit("yedek silinemedi: erisim engellendi (ğ)")
    assert "erisim engellendi" in (tmp_path / "yedek.log").read_text(encoding="utf-8")


def test_log_failure_never_breaks_the_backup(monkeypatch):
    """A backup that cannot write its log still has to take the backup."""
    monkeypatch.setattr(backup, "LOG_FILE", Path("Z:/yok/olmayan/yedek.log"))
    monkeypatch.setattr(sys, "stdout", None)
    backup._emit("hedef yazilamaz")        # must not raise

    with pytest.raises(OSError):
        # Guard against the assertion above passing for the wrong reason:
        # the path really is unwritable, so _emit swallowed a real error.
        Path("Z:/yok/olmayan/yedek.log").write_text("x", encoding="utf-8")


def test_a_test_run_does_not_append_to_the_operators_backup_log(tmp_path, monkeypatch):
    """The production log is a record kept for a person, not for the suite.

    Thirty percent of it - 1516 lines of 5003 - had come from pytest temp
    directories, so the file an operator opens to answer "did last night's
    backup run" was mostly machine noise. run.py guards its own startup log
    the same way.

    The guard has to be narrow: the tests above monkeypatch LOG_FILE to a tmp
    dir precisely so they can assert on what was written, and those still
    have to work. So it skips only the real path, only under pytest.
    """
    from micofx import paths

    real = backup._REAL_LOG_FILE
    assert real == paths.LOG_DIR / "yedek.log", "koruma gercek yolu tanimali"

    before = real.read_text(encoding="utf-8") if real.exists() else ""
    monkeypatch.setattr(backup, "LOG_FILE", real)
    backup._log_line("bu satir gercek loga gitmemeli\n")
    after = real.read_text(encoding="utf-8") if real.exists() else ""
    assert after == before, "pytest altinda uretim logu yazilmamali"

    # A redirected log still records, or the tests above would be testing nothing.
    monkeypatch.setattr(backup, "LOG_FILE", tmp_path / "yedek.log")
    backup._log_line("bu satir gitmeli\n")
    assert "bu satir gitmeli" in (tmp_path / "yedek.log").read_text(encoding="utf-8")
