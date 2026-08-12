"""A backup without the settings database is not a backup.

backup.py already says this in its own words, next to the fix for the way it
used to happen: an exception partway through left a well-formed zip behind,
"looks like a backup, carries a current timestamp, and is missing the settings
DB: the one file in it that cannot be recovered from git." Worse, _prune ranks
by mtime and never opens anything, so those decoys occupy the keep quota and
evict real backups - measured at the time as three failed runs leaving three
archives and zero containing the database.

That fix covered the exception path, via a .part file promoted only on success.
One route stayed open. _snapshot_db returns None - without raising - when the
source database is not where DB_REL says it is, and the caller writes it only
``if snapshot is not None``. The zip then completes normally and is promoted.

_verify_archive is the check that exists specifically to catch database
problems in the finished archive, and it looks for the wrong half of the
property: it reports DECOY entries, any path ending in micofx.db that is not
the wanted one, and never asks whether the wanted one is there at all. An
archive containing no micofx.db produces an empty decoy list and passes.

So the two are split here. A decoy stays a warning - the archive still holds a
good snapshot at the right path, and refusing to produce a backup over it would
trade a restore hazard for no backup at all. An absent database is fatal: that
archive holds only files git already has, and letting it through is what evicts
the real ones.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backup as backup_module

DB_REL = backup_module.DB_REL
WANTED = DB_REL.as_posix()


def _zip(tmp_path: Path, names) -> Path:
    p = tmp_path / "MicoFX_test.zip"
    with zipfile.ZipFile(p, "w") as zf:
        for n in names:
            zf.writestr(n, b"x")
    return p


# ------------------------------------------------------------- the defect

def test_an_archive_with_no_database_is_reported(tmp_path):
    z = _zip(tmp_path, ["run.py", "micofx/engine.py", "config/defaults.json"])
    assert backup_module._database_missing(z) is True, (
        "veritabani olmayan arsiv sessizce gecti - _prune bunu gercek bir "
        "yedegin yerine koyar")


def test_an_archive_that_has_it_is_not_reported(tmp_path):
    z = _zip(tmp_path, ["run.py", WANTED])
    assert backup_module._database_missing(z) is False


def test_a_decoy_alone_does_not_satisfy_the_check(tmp_path):
    """The exact shape that made this hard to see: something ending in
    micofx.db is present, but not at the path a restore reads."""
    z = _zip(tmp_path, ["run.py", ".pytest_tmp/scratch/" + DB_REL.name])
    assert backup_module._database_missing(z) is True


# --------------------------------------------------- decoys still only warn

def test_the_decoy_check_still_finds_them(tmp_path):
    z = _zip(tmp_path, [WANTED, ".pytest_tmp/a/" + DB_REL.name,
                        ".pytest_tmp/b/" + DB_REL.name])
    decoys = backup_module._verify_archive(z)
    assert len(decoys) == 2
    assert WANTED not in decoys, "dogru yoldaki DB sahte diye sayilmamali"


def test_a_clean_archive_reports_no_decoys(tmp_path):
    assert backup_module._verify_archive(_zip(tmp_path, ["run.py", WANTED])) == []


def test_the_two_checks_are_independent(tmp_path):
    """Present-and-polluted is a warning; absent is fatal. An archive can be
    both, and each must answer for itself."""
    z = _zip(tmp_path, ["x/" + DB_REL.name])
    assert backup_module._database_missing(z) is True
    assert backup_module._verify_archive(z) == ["x/" + DB_REL.name]


# --------------------------------------------------- snapshot's silent None

def test_a_missing_source_database_snapshots_to_none(tmp_path):
    """The route that reaches the defect: no raise, just None, and the caller
    writes the entry only when it is not None."""
    assert backup_module._snapshot_db(tmp_path / "yok.db", tmp_path) is None


def test_a_real_source_database_snapshots(tmp_path):
    import sqlite3

    src = tmp_path / "micofx.db"
    con = sqlite3.connect(src)
    con.execute("create table t (a int)")
    con.execute("insert into t values (1)")
    con.commit()
    con.close()

    workdir = tmp_path / "w"
    workdir.mkdir()
    out = backup_module._snapshot_db(src, workdir)
    assert out is not None and out.exists()
    assert sqlite3.connect(out).execute("select a from t").fetchone() == (1,)
