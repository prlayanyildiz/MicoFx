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
    dest_dir = Path(store.system.backup_dir)
    keep = max(1, int(store.system.backup_keep))
    store.close()

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
