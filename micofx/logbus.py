from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Any, Literal

from .paths import LOG_DIR

Level = Literal["DEBUG", "INFO", "WARN", "ERROR", "TRADE", "SIGNAL", "OPT", "AI", "CFG"]

# SIGNAL is here because it is bar-gated, not poll-gated. All three emission
# sites sit behind a "this bar already handled" return (primary and secondary
# signal refresh) or fire once on a state transition (the cross-signal skip),
# so the level produces about 132 lines a day across ten symbols - measured
# from the entry-block counters over a 38.7 hour window - which is 11 KB
# against a 4 MB rotation limit, three tenths of one percent.
#
# It was grouped with INFO/DEBUG under one flood argument that only ever
# applied to them. The cost of that grouping is specific: a SIGNAL line is the
# only record of WHY an entry fired - K, D, ATR, ADX and the higher-timeframe
# bias at the moment the bar closed - and every loss review today could say
# that a trade opened and nothing about what the strategy was looking at. The
# comment beside the emission in engine.py even claimed the loss reviews read
# it back, which they could not: it never reached disk.
# CFG persists for the same reason TRADE does: a symbol's risk settings are
# changed from several doors (panel patch, bulk, optimizer apply) and there was
# no record of any of them. That gap is not academic - max_positions was found
# live at 5 across all ten symbols on 13.08 with a rollback file saying 10 and
# both the dataclass default and defaults.json saying 1, and the log could not
# say who wrote it or when. A settings change is not a warning, so it gets its
# own level rather than being filed under one.
_PERSIST: set[str] = {"WARN", "ERROR", "TRADE", "OPT", "AI", "SIGNAL", "CFG"}
_MAX_FILE_BYTES = 4 * 1024 * 1024
_RING = 1500


class LogBus:
    """In-memory ring buffer for the web terminal, with a rotating file sink.

    Only levels in ``_PERSIST`` reach disk; INFO and DEBUG stay in memory so a
    1-2 second poll loop cannot flood the log file. That argument is about
    per-poll emission and does not reach SIGNAL, which is bar-gated - see the
    note on ``_PERSIST``.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Separate from _lock on purpose. The ring buffer is read by the web
        # thread on every terminal poll; holding that same lock across a disk
        # write (OneDrive/antivirus can stall a write for hundreds of ms) would
        # block the UI on IO. A dedicated file lock still serialises writers -
        # which _write_file needs, see its docstring - without coupling them.
        self._file_lock = threading.Lock()
        self._buf: deque[dict[str, Any]] = deque(maxlen=_RING)
        self._seq = 0
        self._file = LOG_DIR / "micofx.log"

    def emit(self, message: str, level: Level = "INFO", symbol: str = "") -> None:
        # One physical line: a payload with CR/LF must not mint a second
        # timestamped TRADE row that rotation would keep as a whole line.
        message = str(message).replace("\r", " ").replace("\n", " ")
        symbol = str(symbol).replace("\r", " ").replace("\n", " ")
        ts = time.time()
        with self._lock:
            self._seq += 1
            entry = {
                "id": self._seq,
                "ts": ts,
                "time": time.strftime("%H:%M:%S", time.localtime(ts)),
                "level": level,
                "symbol": symbol,
                "message": message,
            }
            self._buf.append(entry)
        if level in _PERSIST:
            self._write_file(entry)

    def _write_file(self, entry: dict[str, Any]) -> None:
        """Append one line, rotating the file when it outgrows _MAX_FILE_BYTES.

        Serialised on ``_file_lock``. Callers reach here from at least four
        threads (engine poll loop, optimizer worker, supervisor review, web
        request handlers) and the rotation is a read-whole-file / truncate /
        rewrite sequence - unsynchronised, a second thread appending in the
        middle of that window has its line silently dropped by the truncate,
        and two threads both deciding to rotate rewrite each other's tail. A
        TRADE line disappearing from the audit trail exactly when the system
        is busiest is the failure mode that matters here.
        """
        with self._file_lock:
            try:
                LOG_DIR.mkdir(parents=True, exist_ok=True)
                if self._file.exists() and self._file.stat().st_size > _MAX_FILE_BYTES:
                    self._rotate()
                stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry["ts"]))
                sym = f"[{entry['symbol']}] " if entry["symbol"] else ""
                with self._file.open("a", encoding="utf-8") as fh:
                    fh.write(f"{stamp} {entry['level']:6} {sym}{entry['message']}\n")
            except OSError:
                # Disk full, file locked by a sync client, permissions - the
                # in-memory ring already has the entry and the web terminal
                # still shows it, so losing the disk copy must never take the
                # caller (an order path, in the worst case) down with it.
                pass

    def _rotate(self) -> None:
        """Halve the file, keeping the newest whole lines and saying so.

        Caller holds ``_file_lock``.

        Three things the previous one-liner got wrong, all visible in a real
        rotation this file went through:

        * it sliced the decoded *text*, so ``[-_MAX_FILE_BYTES // 2:]`` counted
          CHARACTERS against a budget expressed in bytes. Every Turkish
          character in a log line is two bytes, so the file came back over its
          own target - measured at 1.01x on pure-ASCII content and worse on
          real messages.
        * the slice landed at an arbitrary offset, so the file began with half
          a line: ``di -> 3421.55512 (kar 2.34xATR)``. That is the first thing
          anyone reads when they open the log to investigate something.
        * nothing recorded that history had been dropped. An audit trail that
          silently loses its past and still looks continuous is worse than one
          that admits the gap - this is the file an operator reaches for after
          an unexplained fill.
        """
        raw = self._file.read_bytes()
        keep = raw[-(_MAX_FILE_BYTES // 2):]
        # Start at a line boundary. Without this the first line is whatever
        # the byte offset happened to land in the middle of.
        cut = keep.find(b"\n")
        keep = keep[cut + 1:] if cut >= 0 else b""
        dropped = len(raw) - len(keep)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        note = (f"{stamp} WARN   [SISTEM] Log dosyasi {_MAX_FILE_BYTES // 1024} KB "
                f"sinirini asti; en eski {dropped // 1024} KB dusuruldu. "
                f"Daha eski kayitlar gece yedegindeki arsivlerde.\n")
        # Written beside the log and moved into place, not written over it.
        # ``write_bytes`` opens for truncate first, so between that and the end
        # of a two-megabyte write the log is a partial file - and a process
        # killed in that window loses the WHOLE history, not the old half this
        # is meant to drop. Rotation is rare (roughly every five weeks at the
        # current rate), which is exactly why the failure would be unexplainable
        # when it happened.
        #
        # backup.py already does this for the same reason, with a .part it
        # promotes only once the archive is complete. os.replace is atomic
        # within a volume on Windows as well as POSIX.
        tmp = self._file.with_suffix(self._file.suffix + ".part")
        tmp.write_bytes(note.encode("utf-8") + keep)
        os.replace(tmp, self._file)

    def recent(self, after_id: int = 0, limit: int = 400, levels: list[str] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            items = [e for e in self._buf if e["id"] > after_id]
        if levels:
            wanted = set(levels)
            items = [e for e in items if e["level"] in wanted]
        return items[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()

    @property
    def file_path(self):
        return self._file


LOG = LogBus()
