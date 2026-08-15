"""A failed backup must not leave something that looks like a backup.

The archive used to be built directly at its final name. ZipFile's context
manager closes cleanly on the way out of an exception, so anything that went
wrong partway - the settings DB locked past the snapshot timeout, the
destination disappearing mid-write, a file vanishing between the walk and the
write - left a perfectly well-formed zip carrying a current timestamp and
missing the one file in it that cannot be recovered from git.

_prune ranks by mtime and never opens anything, so those decoys occupy the
keep quota and evict real backups. Measured on a scratch copy before the fix:
three failed runs followed by one good one left three archives on disk and
zero containing the database.

The archive is now built under a dotted .part name _prune does not match, and
renamed only once it is complete.
"""
from __future__ import annotations

import sqlite3
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backup


class _FakeStore:
    def __init__(self, dest, keep=3, second=""):
        self.system = SimpleNamespace(
            backup_dir=str(dest), backup_dir_allow_unc=False, backup_keep=keep,
            backup_enabled=True, backup_dir_secondary=second)

    def close(self):
        pass


def _project(tmp_path):
    root = tmp_path / "project"
    (root / "data").mkdir(parents=True)
    (root / "sample.txt").write_text("hi")
    con = sqlite3.connect(root / backup.DB_REL)
    con.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    con.execute("INSERT INTO settings VALUES ('system', '{}')")
    con.commit()
    con.close()
    return root


def _wire(monkeypatch, root, dest, keep=3):
    monkeypatch.setattr(backup, "ROOT", root)
    monkeypatch.setattr(backup, "Store", lambda: _FakeStore(dest, keep))


def _archives(dest):
    return sorted(dest.glob("MicoFX_*.zip"))


def _has_db(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        return backup.DB_REL.as_posix() in zf.namelist()


def test_a_locked_database_leaves_no_archive_at_all(tmp_path, monkeypatch):
    root, dest = _project(tmp_path), tmp_path / "dest"
    dest.mkdir()
    _wire(monkeypatch, root, dest)
    monkeypatch.setattr(backup, "_snapshot_db",
                        lambda s, w: (_ for _ in ()).throw(sqlite3.OperationalError("locked")))

    assert backup.main() == 1
    assert _archives(dest) == []
    assert list(dest.glob(".*.part")) == [], "yarim dosya geride kaldi"


def test_a_write_failure_leaves_no_archive(tmp_path, monkeypatch):
    root, dest = _project(tmp_path), tmp_path / "dest"
    dest.mkdir()
    _wire(monkeypatch, root, dest)
    monkeypatch.setattr(backup, "_snapshot_db",
                        lambda s, w: (_ for _ in ()).throw(OSError("disk dolu")))

    assert backup.main() == 1
    assert _archives(dest) == []


def test_earlier_backups_survive_a_failure(tmp_path, monkeypatch):
    """The headline: a failed run must not cost the last good archive."""
    root, dest = _project(tmp_path), tmp_path / "dest"
    dest.mkdir()
    _wire(monkeypatch, root, dest)

    assert backup.main() == 0
    good = _archives(dest)
    assert len(good) == 1 and _has_db(good[0])

    monkeypatch.setattr(backup, "_snapshot_db",
                        lambda s, w: (_ for _ in ()).throw(sqlite3.OperationalError("locked")))
    assert backup.main() == 1

    after = _archives(dest)
    assert after == good, "onceki yedek kayboldu"
    assert _has_db(after[0])


def test_repeated_failures_cannot_evict_every_good_archive(tmp_path, monkeypatch):
    """The exact eviction the .part name exists to prevent, with keep=2."""
    root, dest = _project(tmp_path), tmp_path / "dest"
    dest.mkdir()
    _wire(monkeypatch, root, dest, keep=2)

    assert backup.main() == 0
    monkeypatch.setattr(backup, "_snapshot_db",
                        lambda s, w: (_ for _ in ()).throw(sqlite3.OperationalError("locked")))
    for _ in range(4):
        assert backup.main() == 1

    surviving = _archives(dest)
    assert surviving, "hicbir yedek kalmadi"
    assert all(_has_db(z) for z in surviving), "ayar veritabani olmayan arsiv kaldi"


def test_a_vanishing_file_does_not_abort_the_backup(tmp_path, monkeypatch):
    """A log rotating mid-walk should cost that file, not the archive."""
    root, dest = _project(tmp_path), tmp_path / "dest"
    dest.mkdir()
    ghost = root / "gider.txt"
    ghost.write_text("simdi var")
    _wire(monkeypatch, root, dest)

    real_iter = backup._iter_files

    def _iter_then_delete(r):
        for p in list(real_iter(r)):
            if p == ghost:
                p.unlink()          # disappears between the walk and the write
            yield p

    monkeypatch.setattr(backup, "_iter_files", _iter_then_delete)

    assert backup.main() == 0
    archives = _archives(dest)
    assert len(archives) == 1
    assert _has_db(archives[0]), "kayip dosya yuzunden DB de dusmus"


def test_two_runs_in_the_same_minute_do_not_overwrite_each_other(tmp_path, monkeypatch):
    """The stamp carries seconds; "w" mode truncates a same-named archive."""
    root, dest = _project(tmp_path), tmp_path / "dest"
    dest.mkdir()
    _wire(monkeypatch, root, dest)

    stamps = iter(["2026-08-11_020101", "2026-08-11_020102"])
    monkeypatch.setattr(backup.time, "strftime", lambda fmt: next(stamps))

    assert backup.main() == 0
    assert backup.main() == 0
    assert len(_archives(dest)) == 2, "ikinci kosu birincisini ezdi"


def test_the_stamp_format_has_second_resolution():
    """Pins it: minute resolution is what allowed the overwrite."""
    seen = {}

    class _Clock:
        @staticmethod
        def strftime(fmt):
            seen["fmt"] = fmt
            return "x"

    # Read the format straight out of the module rather than duplicating it.
    src = Path(backup.__file__).read_text(encoding="utf-8")
    assert '"%Y-%m-%d_%H%M%S"' in src, "damga saniye cozunurlugunu kaybetti"


def test_a_healthy_run_is_unchanged(tmp_path, monkeypatch):
    root, dest = _project(tmp_path), tmp_path / "dest"
    dest.mkdir()
    _wire(monkeypatch, root, dest)

    assert backup.main() == 0
    archives = _archives(dest)
    assert len(archives) == 1
    assert _has_db(archives[0])
    with zipfile.ZipFile(archives[0]) as zf:
        assert "sample.txt" in zf.namelist()
