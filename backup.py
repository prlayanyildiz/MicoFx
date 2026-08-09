"""MicoFX - scheduled evening backup.

Zips the project (excluding .venv/__pycache__/.pytest_cache) into a
timestamped archive under the destination configured in the web panel's
System tab (system.backup_dir), and keeps only the most recent
system.backup_keep archives. Invoked by the "MicoFX Aksam Yedegi" Windows
scheduled task; safe to run manually too.
"""
from __future__ import annotations

import sys
import time
import zipfile
from pathlib import Path

from micofx.paths import ROOT
from micofx.store import Store

EXCLUDE_DIRS = {".venv", "__pycache__", ".pytest_cache", ".git"}


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part in EXCLUDE_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def main() -> int:
    store = Store()
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

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in _iter_files(ROOT):
            zf.write(f, f.relative_to(ROOT))

    print(f"Yedek olusturuldu: {zip_path}")

    existing = sorted(dest_dir.glob("MicoFX_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in existing[keep:]:
        print(f"Eski yedek siliniyor: {old.name}")
        old.unlink()

    print(f"Tamamlandi. Guncel yedek sayisi: {len(list(dest_dir.glob('MicoFX_*.zip')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
