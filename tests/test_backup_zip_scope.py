"""backup.py's file walk must skip .git along with the existing
build-artifact excludes (B3) - full commit history has no business in a
timestamped config/state snapshot, and it can dwarf the rest of the archive.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backup


def test_git_dir_excluded_from_backup_walk(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main")
    (tmp_path / "micofx.db").write_text("data")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_text("x")

    found = {p.relative_to(tmp_path).as_posix() for p in backup._iter_files(tmp_path)}

    assert "micofx.db" in found
    assert not any(f.startswith(".git/") for f in found)
    assert not any(f.startswith("__pycache__/") for f in found)


def test_exclude_dirs_includes_git():
    assert ".git" in backup.EXCLUDE_DIRS


def test_pytest_tmp_is_excluded():
    """A --basetemp=.pytest_tmp run leaves fixtures in the workspace.

    That is not hypothetical: two nightly archives went out carrying 23 of
    them, seven being scratch copies of a settings DB.
    """
    assert ".pytest_tmp" in backup.EXCLUDE_DIRS


def test_walk_skips_a_leftover_pytest_tmp_tree(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "micofx.db").write_text("real")
    junk = tmp_path / ".pytest_tmp" / "test_something0" / "project" / "data"
    junk.mkdir(parents=True)
    (junk / "micofx.db").write_text("decoy")
    (tmp_path / "keep.txt").write_text("keep")

    found = {p.relative_to(tmp_path).as_posix() for p in backup._iter_files(tmp_path)}

    assert "keep.txt" in found
    assert not any(f.startswith(".pytest_tmp/") for f in found)
    # The real DB is added separately from a snapshot, so the walk skips it too.
    assert not any(f.endswith("micofx.db") for f in found)


def test_verify_archive_flags_a_decoy_settings_db(tmp_path):
    """The restore trap, caught generically rather than by folder name.

    ".pytest_tmp/" sorts before "data/", so a restore that picks the first
    path ending in micofx.db gets an empty database back. EXCLUDE_DIRS only
    knows the junk somebody already met; this knows the shape of the damage.
    """
    import zipfile

    archive = tmp_path / "MicoFX_test.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(".pytest_tmp/t0/project/data/micofx.db", "decoy")
        zf.writestr("data/micofx.db", "real")
        zf.writestr("run.py", "code")

    decoys = backup._verify_archive(archive)
    assert decoys == [".pytest_tmp/t0/project/data/micofx.db"]


def test_verify_archive_is_quiet_on_a_clean_one(tmp_path):
    import zipfile

    archive = tmp_path / "MicoFX_clean.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("data/micofx.db", "real")
        zf.writestr("micofx/engine.py", "code")

    assert backup._verify_archive(archive) == []
