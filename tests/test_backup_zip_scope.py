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
