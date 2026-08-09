from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Literal

from .paths import LOG_DIR

Level = Literal["DEBUG", "INFO", "WARN", "ERROR", "TRADE", "SIGNAL", "OPT", "AI"]

_PERSIST: set[str] = {"WARN", "ERROR", "TRADE", "OPT", "AI"}
_MAX_FILE_BYTES = 4 * 1024 * 1024
_RING = 1500


class LogBus:
    """In-memory ring buffer for the web terminal, with a rotating file sink.

    Only levels in ``_PERSIST`` reach disk; INFO/DEBUG/SIGNAL stay in memory so a
    1-2 second poll loop cannot flood the log file.
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
                    keep = self._file.read_text(encoding="utf-8", errors="replace")[-_MAX_FILE_BYTES // 2:]
                    self._file.write_text(keep, encoding="utf-8")
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
