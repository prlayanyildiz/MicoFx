"""MicoFX - scheduled evening backup.

Zips the project (skipping the throwaway trees in EXCLUDE_DIRS) into a
timestamped archive under the destination configured in the web panel's
System tab (system.backup_dir), optionally copied to a second destination,
keeping only the most recent system.backup_keep archives at each. Invoked by
the "MicoFX Aksam Yedegi" Windows scheduled task; safe to run manually too.

The settings DB goes in as a consistent sqlite snapshot rather than a live
file copy (_snapshot_db), and the finished archive is checked for stray
duplicates of it (_verify_archive) - it is the only file in here that cannot
be recovered from git, so it is the only one worth being careful about.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from micofx.paths import DB_PATH, ROOT
from micofx.store import Store

# Throwaway trees that must never reach an archive. ``.pytest_tmp`` is here
# because it actually happened: a test run started with
# ``--basetemp=.pytest_tmp`` leaves its fixtures in the workspace, and two
# nightly archives went out carrying 23 of them - including seven scratch
# copies of a settings DB (see _verify_archive for why that specifically is
# dangerous).
# ``.tmp.driveupload`` / ``.tmp.drivedownload`` are the Google Drive desktop
# client's contract: it creates both in every folder it syncs, filled with
# numbered temp chunks (measured 16.08: one 3.4 MB). They are not project
# files. .gitignore already lists them (b05d706); the archive walk must too,
# or a future Drive re-bind silently packs the sync junk.
EXCLUDE_DIRS = {
    ".venv", "__pycache__", ".pytest_cache", ".pytest_tmp", ".git",
    ".tmp.driveupload", ".tmp.drivedownload",
}

# Where the settings DB sits inside the project, resolved once at import
# against the real paths. Everything below goes through ``ROOT / DB_REL``
# rather than the absolute DB_PATH so the walk still lines up when ROOT is
# pointed somewhere else (the tests do exactly that).
DB_REL = DB_PATH.relative_to(ROOT)


LOG_FILE = ROOT / "logs" / "yedek.log"


def _stamp() -> str:
    """Archive-name timestamp, seconds included so two runs in one minute
    cannot land on the same file name.

    Its own function rather than a bare ``time.strftime`` call because the
    log line needs a timestamp too, and a test that patched the shared
    ``time.strftime`` to control this one starved the other.
    """
    return time.strftime("%Y-%m-%d_%H%M%S")


def _log_line(text: str) -> None:
    """Append to the backup log, the only witness when there is no console.

    The scheduled task runs pythonw, so a job whose sole record was the
    task exit code failed quietly for two nights before anyone looked.
    Best effort: a backup must not fail because its log could not be
    written.
    """
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as fh:
            fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text)
    except Exception:
        pass


def _emit(msg: str) -> None:
    """Write one operator line that must not die on a cp1252 console.

    Windows task history captures stdout. Turkish OSError text carries
    ``ğ`` (U+011F); ``print`` on cp1252 raises UnicodeEncodeError and
    swallows the original failure. Measured 16.08 on this machine.
    """
    text = msg if msg.endswith("\n") else msg + "\n"
    _log_line(text)
    stream = sys.stdout
    if stream is None:
        # pythonw: no console exists. The write used to raise
        # AttributeError straight out of the script, which is why the
        # task returned 1 on 17.08 while running it by hand worked.
        return
    try:
        stream.write(text)
        stream.flush()
    except UnicodeEncodeError:
        # Listed before the broad clause below on purpose: UnicodeEncodeError
        # is a ValueError, so catching ValueError first would swallow it and
        # skip the buffer fallback the cp1252 console needs.
        encoding = getattr(stream, "encoding", None) or "utf-8"
        buf = getattr(stream, "buffer", None)
        if buf is not None:
            buf.write(text.encode(encoding, errors="replace"))
            buf.flush()
            return
        stream.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))
        stream.flush()
    except (AttributeError, ValueError, OSError):
        # A stream that exists but cannot be written: closed handle, dropped
        # redirection. The line is already in the log.
        return


def _iter_files(root: Path, skipped: list[int] | None = None):
    """Yield backup candidates. Unreadable paths are counted, not fatal.

    Exclude-dirs are pruned before any ``stat``: ``Path.rglob`` + ``is_dir``
    died on a ``.pytest_tmp\\*current`` junction (WinError 1463) before the
    exclude list was consulted.
    """
    box = skipped if skipped is not None else [0]
    db = root / DB_REL

    def onerror(_err: OSError) -> None:
        box[0] += 1

    for dirpath, dirnames, filenames in os.walk(root, onerror=onerror, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        here = Path(dirpath)
        try:
            rel_dir = here.relative_to(root)
        except ValueError:
            continue
        if any(part in EXCLUDE_DIRS for part in rel_dir.parts):
            dirnames[:] = []
            continue
        for name in filenames:
            path = here / name
            try:
                rel = path.relative_to(root)
            except (OSError, ValueError):
                box[0] += 1
                continue
            if any(part in EXCLUDE_DIRS for part in rel.parts):
                continue
            # The settings DB is added separately from a consistent snapshot (see
            # _snapshot_db) - this task normally runs with the bot live, and
            # zipfile reading the file page by page while the engine writes to it
            # produces a torn copy. Its sidecar journal/WAL files would only ever
            # describe the live database, never the snapshot, so they go too.
            if path == db or path.name.startswith(db.name + "-"):
                continue
            try:
                if path.is_dir():
                    continue
            except OSError:
                box[0] += 1
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


def _verify_archive(zip_path: Path) -> list[str]:
    """Report any decoy settings DB in the finished archive.

    EXCLUDE_DIRS is a list of names, so it only ever catches junk somebody has
    already seen. This catches the class instead, and it is the one thing worth
    catching: the archive is supposed to contain exactly one ``micofx.db`` -
    the consistent snapshot at ``data/micofx.db``. When two nightly archives
    picked up a stray ``.pytest_tmp`` tree they ended up with eight, seven of
    them 12 KB scratch fixtures. The real one was intact, but ``.pytest_tmp/``
    sorts before ``data/``, so restoring by "first path ending in micofx.db"
    silently hands back an empty database.

    Returns the offending entry names; the caller warns rather than failing.
    A polluted archive still holds a good snapshot at the right path, and
    refusing to produce a backup over this would trade a restore hazard for
    no backup at all.
    """
    wanted = DB_REL.as_posix()
    with zipfile.ZipFile(zip_path) as zf:
        return [n for n in zf.namelist()
                if n.endswith(DB_REL.name) and n != wanted]


def _database_missing(zip_path: Path) -> bool:
    """True when the finished archive has no settings DB at the restore path.

    The companion to _verify_archive, which reports the wrong half of the same
    property: it lists DECOY entries - anything ending in micofx.db that is not
    the wanted path - and never asks whether the wanted one is there. An archive
    containing no micofx.db at all therefore produced an empty decoy list and
    passed.

    That is the state this module already describes as the bad one: it looks
    like a backup, carries a current timestamp, and is missing the one file in
    it that cannot be recovered from git. The .part promotion closed the route
    where an exception left such an archive behind; this closes the quiet one,
    where _snapshot_db returns None because the source database is not where
    DB_REL says it is, and the caller writes the entry only when it is not None.

    Unlike a decoy this is fatal to the run. A polluted archive still holds a
    good snapshot at the right path, so warning is the proportionate answer
    there. An archive with no database holds only files git already has - and
    _prune, which ranks by mtime and never opens anything, would let it evict a
    real backup.
    """
    wanted = DB_REL.as_posix()
    with zipfile.ZipFile(zip_path) as zf:
        return wanted not in zf.namelist()


def _prune(folder: Path, keep: int) -> None:
    """Keep only the ``keep`` newest archives in ``folder``."""
    existing = sorted(folder.glob("MicoFX_*.zip"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
    for old in existing[keep:]:
        # Full path, not folder.name: both destinations are usually called
        # "MicoFX_Yedek", so the short form made the one line that says
        # something was DELETED unable to say from where.
        _emit(f"Eski yedek siliniyor: {old}")
        try:
            old.unlink()
        except OSError as exc:
            _emit(f"UYARI: eski yedek silinemedi ({old}): {exc}")


def main() -> int:
    try:
        store = Store()
    except RuntimeError as exc:
        # Unattended scheduled task: a broken settings DB must produce a
        # readable line in the task history, not a traceback.
        _emit(f"HATA: {exc}")
        return 1
    enabled = bool(getattr(store.system, "backup_enabled", True))
    raw_dir = str(store.system.backup_dir)
    raw_second = str(getattr(store.system, "backup_dir_secondary", "") or "").strip()
    allow_unc = bool(store.system.backup_dir_allow_unc)
    keep = max(1, int(store.system.backup_keep))
    store.close()

    if not enabled:
        # Deliberately off, so exit 0: the Windows task still fires nightly and
        # a non-zero result here would show up as a failing scheduled task
        # forever, which is exactly how a real failure later gets ignored.
        _emit("Otomatik yedekleme kapali (Sistem > backup_enabled). Yedek alinmadi.")
        return 0

    # PATCH /api/system already refuses to WRITE a UNC backup_dir without
    # this flag (see web/app.py) - this is the read side of that same gate.
    # A UNC value could still be sitting in the DB from before that check
    # existed (or a config seeded outside the API), and this scheduled task
    # runs unattended - it must not silently keep sending the whole project
    # + settings DB over the network run after run just because nothing
    # re-validates the stored value at execution time.
    def _is_unc(path: str) -> bool:
        return path.startswith("\\\\") or path.startswith("//")

    if _is_unc(raw_dir) and not allow_unc:
        _emit(f"HATA: yedek konumu UNC ({raw_dir!r}) ama backup_dir_allow_unc kapali - "
              f"yedek yazilmadi. Web panelinden System > backup_dir_allow_unc:true "
              f"yapin veya yerel bir yol secin.")
        return 1
    # The secondary destination goes through the same gate rather than being
    # trusted for being "just a copy" - it receives the identical archive,
    # settings DB included.
    if raw_second and _is_unc(raw_second) and not allow_unc:
        _emit(f"UYARI: ikincil yedek konumu UNC ({raw_second!r}) ama "
              f"backup_dir_allow_unc kapali - ikincil kopya atlandi.")
        raw_second = ""

    # A drive letter that is not mounted (D: on a machine that has none, a USB
    # stick left unplugged, a disconnected network drive) used to raise
    # FileNotFoundError straight out of mkdir. Under the scheduled task that is
    # a bare traceback in a window nobody sees, so the operator learns their
    # backups stopped whenever they next need one.
    dest_dir = Path(raw_dir)
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _emit(f"HATA: yedek konumu kullanilamiyor ({raw_dir}): {exc}\n"
              f"Surucu takili degil veya yol yanlis olabilir. Web panelinden "
              f"Sistem > 'Yedek konumu' alanini bu makinede gercekten var olan "
              f"bir klasore ayarlayin (orn. C:\\MicoFX_Yedek), ya da otomatik "
              f"yedeklemeyi kapatin.")
        return 1

    # Seconds in the stamp, not just minutes. The archive is opened "w", so two
    # runs landing in the same minute silently truncated the first one - which
    # is exactly what a manual re-run after a failed attempt looks like.
    stamp = _stamp()
    zip_path = dest_dir / f"MicoFX_{stamp}.zip"
    # Built under a name _prune does not match, and renamed only once the
    # archive is complete. Anything that goes wrong partway - the DB locked
    # past the snapshot timeout, the destination disappearing mid-write, a
    # file vanishing between the walk and the write - used to leave a
    # perfectly well-formed zip behind, because ZipFile's context manager
    # closes cleanly on the way out of an exception. That archive looks like a
    # backup, carries a current timestamp, and is missing the settings DB: the
    # one file in it that cannot be recovered from git.
    #
    # _prune ranks by mtime and never opens anything, so those decoys occupy
    # the keep quota and evict real backups. Measured on a scratch copy: three
    # failed runs followed by one good one left three archives on disk and
    # zero containing the database.
    part_path = dest_dir / f".MicoFX_{stamp}.zip.part"

    workdir = Path(tempfile.mkdtemp(prefix="micofx-backup-"))
    try:
        try:
            with zipfile.ZipFile(part_path, "w", zipfile.ZIP_DEFLATED) as zf:
                skipped = [0]
                for f in _iter_files(ROOT, skipped):
                    try:
                        zf.write(f, f.relative_to(ROOT))
                    except (OSError, ValueError) as exc:
                        # A file that disappeared between the walk and the
                        # write (a log rotating, a temp file cleaned up) must
                        # not cost the whole backup - note it and carry on.
                        _emit(f"UYARI: atlandi ({f}): {exc}")
                        skipped[0] += 1
                if skipped[0]:
                    _emit(f"UYARI: {skipped[0]} yol okunamadi, atlandi.")
                snapshot = _snapshot_db(ROOT / DB_REL, workdir)
                if snapshot is not None:
                    zf.write(snapshot, DB_REL)
                    _emit(f"Ayar veritabani tutarli anlik goruntu olarak eklendi "
                          f"({snapshot.stat().st_size} bayt).")
        except (OSError, sqlite3.Error) as exc:
            # Unattended task: a readable line, and no half-archive left
            # claiming to be a backup.
            part_path.unlink(missing_ok=True)
            _emit(f"HATA: yedek olusturulamadi: {exc}\n"
                  f"Onceki yedekler oldugu gibi birakildi.")
            return 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    # Checked on the .part, before it becomes a backup: an archive without the
    # database must never reach the folder _prune ranks, or it takes a real
    # one's place there.
    if _database_missing(part_path):
        part_path.unlink(missing_ok=True)
        _emit(f"HATA: arsivde '{DB_REL.as_posix()}' yok - bu bir yedek degil.")
        _emit(f"  Kaynak veritabani beklenen yerde mi: {ROOT / DB_REL}")
        _emit("  Onceki yedekler oldugu gibi birakildi.")
        return 1

    try:
        part_path.replace(zip_path)
    except OSError as exc:
        part_path.unlink(missing_ok=True)
        _emit(f"HATA: yedek adlandirilamadi ({zip_path}): {exc}")
        return 1

    _emit(f"Yedek olusturuldu: {zip_path}")

    decoys = _verify_archive(zip_path)
    if decoys:
        _emit(f"UYARI: arsivde {len(decoys)} adet fazladan '{DB_REL.name}' var - "
              f"geri yuklerken MUTLAKA '{DB_REL.as_posix()}' yolunu kullanin, "
              f"yol sonuna bakarak secmeyin:")
        for name in decoys[:5]:
            _emit(f"  {name}")
        if len(decoys) > 5:
            _emit(f"  ... ve {len(decoys) - 5} tane daha")
        _emit("  Bunlar muhtemelen proje klasorunde kalmis gecici bir "
              "klasorden geliyor; EXCLUDE_DIRS'e ekleyin.")

    # Copy the finished archive rather than building it twice: a second walk
    # would snapshot the DB again a few seconds later, so the two "copies"
    # could disagree about the state they claim to preserve.
    if raw_second:
        try:
            second_dir = Path(raw_second)
            second_dir.mkdir(parents=True, exist_ok=True)
            second_path = second_dir / zip_path.name
            shutil.copy2(zip_path, second_path)
            _emit(f"Ikincil kopya: {second_path}")
            _prune(second_dir, keep)
        except OSError as exc:
            # Never fatal - see backup_dir_secondary's note in models.py.
            _emit(f"UYARI: ikincil kopya yazilamadi ({raw_second}): {exc}")

    _prune(dest_dir, keep)
    _emit(f"Tamamlandi. Guncel yedek sayisi: {len(list(dest_dir.glob('MicoFX_*.zip')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
