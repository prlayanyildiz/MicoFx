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
