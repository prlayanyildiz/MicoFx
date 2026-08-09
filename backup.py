"""MicoFX - scheduled evening backup.

Zips the project (excluding .venv/__pycache__/.pytest_cache) into a
timestamped archive under the destination configured in the web panel's
System tab (system.backup_dir), and keeps only the most recent
system.backup_keep archives. Invoked by the "MicoFX Aksam Yedegi" Windows
scheduled task; safe to run manually too.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from micofx.paths import DB_PATH, ROOT
from micofx.store import Store

EXCLUDE_DIRS = {".venv", "__pycache__", ".pytest_cache", ".git"}

# Where the settings DB sits inside the project, resolved once at import
# against the real paths. Everything below goes through ``ROOT / DB_REL``
# rather than the absolute DB_PATH so the walk still lines up when ROOT is
# pointed somewhere else (the tests do exactly that).
DB_REL = DB_PATH.relative_to(ROOT)


def _iter_files(root: Path):
    db = root / DB_REL
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in EXCLUDE_DIRS for part in path.relative_to(root).parts):
            continue
        # The settings DB is added separately from a consistent snapshot (see
        # _snapshot_db) - this task normally runs with the bot live, and
        # zipfile reading the file page by page while the engine writes to it
        # produces a torn copy. Its sidecar journal/WAL files would only ever
        # describe the live database, never the snapshot, so they go too.
        if path == db or path.name.startswith(db.name + "-"):
            continue
        yield path


def _snapshot_db(source: Path, workdir: Path) -> Path | None:
    """Consistent copy of the live settings DB via sqlite's online backup.

    Unlike a file copy this coordinates with whatever else has the database
    open: sqlite restarts the copy if a writer commits partway through, so
    the result is always a valid database rather than a mix of two states.
    A backup nobody can restore is worse than no backup, and this is the one
    file in the archive that is being written to while the archive is made.
    """
    if not source.exists():
        return None
    out = workdir / source.name
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=30.0)
    try:
        dst = sqlite3.connect(out)
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return out


def main() -> int:
    try:
        store = Store()
    except RuntimeError as exc:
        # Unattended scheduled task: a broken settings DB must produce a
        # readable line in the task history, not a traceback.
        print(f"HATA: {exc}")
        return 1
    raw_dir = str(store.system.backup_dir)
    allow_unc = bool(store.system.backup_dir_allow_unc)
    keep = max(1, int(store.system.backup_keep))
    store.close()

    # PATCH /api/system already refuses to WRITE a UNC backup_dir without
    # this flag (see web/app.py) - this is the read side of that same gate.
    # A UNC value could still be sitting in the DB from before that check
    # existed (or a config seeded outside the API), and this scheduled task
    # runs unattended - it must not silently keep sending the whole project
    # + settings DB over the network run after run just because nothing
    # re-validates the stored value at execution time.
    is_unc = raw_dir.startswith("\\\\") or raw_dir.startswith("//")
    if is_unc and not allow_unc:
        print(f"HATA: yedek konumu UNC ({raw_dir!r}) ama backup_dir_allow_unc kapali - "
              f"yedek yazilmadi. Web panelinden System > backup_dir_allow_unc:true "
              f"yapin veya yerel bir yol secin.")
        return 1

    dest_dir = Path(raw_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M")
    zip_path = dest_dir / f"MicoFX_{stamp}.zip"

    workdir = Path(tempfile.mkdtemp(prefix="micofx-backup-"))
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in _iter_files(ROOT):
                zf.write(f, f.relative_to(ROOT))
            snapshot = _snapshot_db(ROOT / DB_REL, workdir)
            if snapshot is not None:
                zf.write(snapshot, DB_REL)
                print(f"Ayar veritabani tutarli anlik goruntu olarak eklendi "
                      f"({snapshot.stat().st_size} bayt).")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print(f"Yedek olusturuldu: {zip_path}")

    existing = sorted(dest_dir.glob("MicoFX_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in existing[keep:]:
        print(f"Eski yedek siliniyor: {old.name}")
        old.unlink()

    print(f"Tamamlandi. Guncel yedek sayisi: {len(list(dest_dir.glob('MicoFX_*.zip')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
