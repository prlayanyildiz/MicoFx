"""The settings DB goes into the archive as a consistent sqlite snapshot.

This task normally runs with the bot live. zipfile reading micofx.db page by
page while the engine commits to it yields a torn file - the archive looks
fine, and the one thing in it worth restoring is unusable. Nothing else in
the project is written to while the zip is being built, so this is the only
file that needs the online-backup treatment.
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
    def __init__(self, dest):
        self.system = SimpleNamespace(backup_dir=str(dest), backup_dir_allow_unc=False,
                                      backup_keep=3)

    def close(self):
        pass


def _project(tmp_path):
    root = tmp_path / "project"
    (root / "data").mkdir(parents=True)
    (root / "sample.txt").write_text("hi")
    db = root / backup.DB_REL
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    con.execute("INSERT INTO settings VALUES ('system', '{\"running\": true}')")
    con.commit()
    return root, db, con


def test_archive_carries_a_valid_db_even_with_a_writer_still_attached(tmp_path, monkeypatch):
    root, db, con = _project(tmp_path)
    dest = tmp_path / "dest"
    monkeypatch.setattr(backup, "ROOT", root)
    monkeypatch.setattr(backup, "Store", lambda: _FakeStore(dest))

    try:
        # Uncommitted work in flight from another connection, exactly like the
        # engine mid-cycle when the scheduled task fires.
        con.execute("INSERT INTO settings VALUES ('half', 'written')")
        assert backup.main() == 0
    finally:
        con.close()

    archive = next(iter(dest.glob("MicoFX_*.zip")))
    with zipfile.ZipFile(archive) as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        assert backup.DB_REL.as_posix() in names
        # Exactly once - not both the raw file and the snapshot.
        assert names.count(backup.DB_REL.as_posix()) == 1
        zf.extract(backup.DB_REL.as_posix(), tmp_path / "restored")

    restored = sqlite3.connect(tmp_path / "restored" / backup.DB_REL)
    try:
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        rows = dict(restored.execute("SELECT key, value FROM settings"))
        assert "system" in rows            # committed data survives
    finally:
        restored.close()


def test_live_db_and_its_sidecars_are_skipped_by_the_walk(tmp_path):
    root = tmp_path / "project"
    (root / "data").mkdir(parents=True)
    (root / backup.DB_REL).write_text("live")
    (root / "data" / "micofx.db-wal").write_text("wal")
    (root / "data" / "micofx.db-journal").write_text("journal")
    (root / "keep.txt").write_text("keep")

    found = {p.relative_to(root).as_posix() for p in backup._iter_files(root)}

    assert "keep.txt" in found
    assert backup.DB_REL.as_posix() not in found
    # Sidecars describe the LIVE database, never the snapshot - shipping them
    # alongside a different db file is worse than shipping nothing.
    assert "data/micofx.db-wal" not in found
    assert "data/micofx.db-journal" not in found


def test_snapshot_returns_none_when_there_is_no_db(tmp_path):
    assert backup._snapshot_db(tmp_path / "missing.db", tmp_path) is None
