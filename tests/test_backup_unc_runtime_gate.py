"""backup.py must re-check backup_dir_allow_unc at execution time (M8), not
just trust that PATCH /api/system's write-side gate (see B3/web/app.py) was
always the only path the DB value ever went through - a UNC value could
already be sitting there from before that check existed, and this scheduled
task runs unattended with no one to see a silent write to the wrong network
share.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backup



def _seed_db(root):
    """A real settings DB under the fake project root.

    These cases are about the UNC destination gate, and the fixture never
    needed a database until backup.py started refusing to promote an archive
    without one - which it should, since an archive with no micofx.db holds
    only files git already has. A real run always has it; the fixture was the
    thing that did not.
    """
    import sqlite3

    (root / "data").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(root / "data" / "micofx.db")
    con.execute("create table settings (key text primary key, value text)")
    con.commit()
    con.close()

class _FakeSystem:
    def __init__(self, backup_dir, backup_dir_allow_unc=False, backup_keep=3):
        self.backup_dir = backup_dir
        self.backup_dir_allow_unc = backup_dir_allow_unc
        self.backup_keep = backup_keep


class _FakeStore:
    def __init__(self, system):
        self.system = system
        self.closed = False

    def close(self):
        self.closed = True


def test_backup_refuses_unc_dest_without_allow_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "Store",
                        lambda: _FakeStore(_FakeSystem(r"\\nas\share\backups")))
    monkeypatch.setattr(backup, "ROOT", tmp_path)

    result = backup.main()

    assert result != 0
    # Nothing should have been written anywhere - there is no local dest_dir
    # to even check, since the whole point is refusing before touching one.


def test_backup_allows_unc_dest_with_allow_flag(tmp_path, monkeypatch):
    # project (ROOT) and dest are SIBLINGS, not nested - dest must stay
    # outside ROOT or the zip being written mid-walk would try to include
    # itself (a pre-existing backup.py quirk, not something this test needs
    # to exercise).
    root = tmp_path / "project"
    root.mkdir()
    (root / "sample.txt").write_text("hi")
    _seed_db(root)
    dest = tmp_path / "dest"
    # A syntactically-UNC string is all the gate itself checks (a real UNC
    # share isn't available in a unit test) - redirect Path() to a real local
    # dir only for that exact string, so the write side still exercises
    # actual filesystem I/O instead of stopping at the gate.
    fake_unc = r"\\fake-nas\share\backups"
    real_path = Path
    monkeypatch.setattr(backup, "Path",
                        lambda p: dest if str(p) == fake_unc else real_path(p))
    monkeypatch.setattr(backup, "Store",
                        lambda: _FakeStore(_FakeSystem(fake_unc, backup_dir_allow_unc=True)))
    monkeypatch.setattr(backup, "ROOT", root)

    result = backup.main()

    assert result == 0
    assert list(dest.glob("MicoFX_*.zip"))


def test_backup_allows_local_dest_without_allow_flag(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    (root / "sample.txt").write_text("hi")
    _seed_db(root)
    dest = tmp_path / "dest"
    monkeypatch.setattr(backup, "Store",
                        lambda: _FakeStore(_FakeSystem(str(dest), backup_dir_allow_unc=False)))
    monkeypatch.setattr(backup, "ROOT", root)

    result = backup.main()

    assert result == 0
    assert list(dest.glob("MicoFX_*.zip"))
