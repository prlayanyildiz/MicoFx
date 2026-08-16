"""A backup must survive unreadable paths and a cp1252 console.

Live 16.08: ``MicoFX Aksam Yedegi`` had never produced an archive on this
machine. ``python backup.py`` died in ``_iter_files`` on
``.pytest_tmp\\test_add_symbol_is_born_disablcurrent`` (WinError 1463),
then the except path died again trying to ``print`` the same Turkish
Windows message (``bağlantı``, U+011F) to a cp1252 console.
"""
from __future__ import annotations

import io
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backup

TURKISH_OSERROR = OSError(
    1463,
    "sembolik bağlantı, türü devre dışı bırakıldığından izlenemiyor",
)


def test_an_unstatable_path_does_not_abort_the_walk(tmp_path, monkeypatch):
    (tmp_path / "keep.txt").write_text("ok")
    (tmp_path / "data").mkdir()
    poison = tmp_path / "badcurrent"
    poison.write_text("x")

    orig = Path.is_dir

    def boom(self):
        if self.name == "badcurrent":
            raise TURKISH_OSERROR
        return orig(self)

    monkeypatch.setattr(Path, "is_dir", boom)

    skipped = [0]
    found = {p.name for p in backup._iter_files(tmp_path, skipped)}
    assert "keep.txt" in found
    assert skipped[0] >= 1


def test_pytest_tmp_is_not_stated_at_all(tmp_path, monkeypatch):
    """Exclude must win before any stat: that is the 16.08 crash site."""
    (tmp_path / "keep.txt").write_text("ok")
    junk = tmp_path / ".pytest_tmp"
    junk.mkdir()
    (junk / "test_add_symbol_is_born_disablcurrent").write_text("link")

    stated = []
    orig = Path.is_dir

    def spy(self):
        stated.append(self.name)
        return orig(self)

    monkeypatch.setattr(Path, "is_dir", spy)
    list(backup._iter_files(tmp_path))
    assert "test_add_symbol_is_born_disablcurrent" not in stated


def test_emit_survives_a_cp1252_console(monkeypatch):
    class Cp1252:
        encoding = "cp1252"

        def __init__(self):
            self.buffer = io.BytesIO()

        def write(self, s):
            s.encode("cp1252")  # the live crash
            return len(s)

        def flush(self):
            pass

    fake = Cp1252()
    monkeypatch.setattr(sys, "stdout", fake)
    backup._emit("HATA: yedek olusturulamadi: " + TURKISH_OSERROR.strerror)
    out = fake.buffer.getvalue()
    assert out, "operator mesaji yutuldu"
    assert b"HATA" in out


def test_a_build_error_with_turkish_text_still_exits_1(tmp_path, monkeypatch):
    root = tmp_path / "project"
    (root / "data").mkdir(parents=True)
    con = sqlite3.connect(root / backup.DB_REL)
    con.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    con.execute("INSERT INTO settings VALUES ('system', '{}')")
    con.commit()
    con.close()
    dest = tmp_path / "dest"
    dest.mkdir()

    class Store:
        def __init__(self):
            self.system = SimpleNamespace(
                backup_dir=str(dest), backup_dir_allow_unc=False, backup_keep=3,
                backup_enabled=True, backup_dir_secondary="")

        def close(self):
            pass

    monkeypatch.setattr(backup, "ROOT", root)
    monkeypatch.setattr(backup, "Store", Store)
    monkeypatch.setattr(
        backup, "_snapshot_db",
        lambda s, w: (_ for _ in ()).throw(TURKISH_OSERROR),
    )

    class Cp1252:
        encoding = "cp1252"

        def __init__(self):
            self.buffer = io.BytesIO()

        def write(self, s):
            s.encode("cp1252")
            return len(s)

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", Cp1252())
    assert backup.main() == 1
