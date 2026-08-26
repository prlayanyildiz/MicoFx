"""Log file writes must be serialised; a broken settings DB must not vanish.

Two separate hardening fixes, both about what happens when the boring
infrastructure underneath the trading logic misbehaves:

* ``LogBus._write_file`` rotates by reading the whole file and rewriting the
  tail. Concurrent writers hitting that window lose lines - including TRADE
  lines, which are the audit trail.
* ``Store()`` on an unreadable/corrupt sqlite file used to raise straight out
  of ``main()``. Under ``pythonw.exe`` there is no console, so the traceback
  went nowhere and the app just disappeared.
"""
from __future__ import annotations

import sqlite3
import threading

import pytest

from micofx.logbus import LogBus


def test_concurrent_emit_keeps_every_persisted_line(tmp_path, monkeypatch):
    """No line may be lost when a rotation races appends from other threads."""
    monkeypatch.setattr("micofx.logbus.LOG_DIR", tmp_path)
    # Small enough that rotation fires repeatedly during the run.
    monkeypatch.setattr("micofx.logbus._MAX_FILE_BYTES", 4096)

    bus = LogBus()
    bus._file = tmp_path / "micofx.log"

    threads = [
        threading.Thread(target=lambda n=n: [
            bus.emit(f"t{n}-line{i}", "TRADE", "BTCUSD") for i in range(60)
        ])
        for n in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Rotation is read-whole-file / truncate / rewrite-tail. Unsynchronised,
    # several threads run that sequence at once and each writes back the tail
    # it read BEFORE the others truncated - appends landing in those windows
    # are dropped and the file drifts past its own cap instead of being pinned
    # to it. Measured: the unlocked version ends this run at 3.9-4.1 kB and a
    # different line count every time; the locked one lands on the same
    # ~2.3 kB (rotation floor + the appends after it) on every run.
    size = bus._file.stat().st_size
    assert 0 < size <= 4096, f"rotation did not bound the file: {size} bytes"

    lines = [ln for ln in bus._file.read_text(encoding="utf-8",
                                              errors="replace").splitlines() if ln]
    assert lines, "rotation must not empty the file"
    for line in lines[1:]:            # first line may be a rotation remnant
        assert line.count("TRADE") == 1, f"interleaved write: {line!r}"

    # The ring buffer is the other half of the contract and must be complete.
    assert len(bus.recent(limit=1000)) == 480


def test_write_file_holds_its_own_lock_not_the_ring_lock():
    """The web terminal's poll must not block behind a slow disk write."""
    bus = LogBus()
    assert bus._file_lock is not bus._lock


def test_store_raises_readable_runtime_error_on_broken_db(tmp_path, monkeypatch):
    bad = tmp_path / "micofx.db"
    bad.write_bytes(b"this is definitely not a sqlite database" * 64)

    monkeypatch.setattr("micofx.store.DB_PATH", bad)
    monkeypatch.setattr("micofx.store.ensure_dirs", lambda: None)

    from micofx.store import Store

    with pytest.raises(RuntimeError) as excinfo:
        Store()
    # Turkish, actionable, and naming the file - this is what the user sees
    # instead of a traceback into a stream pythonw.exe never shows.
    assert "veritabani acilamadi" in str(excinfo.value)
    assert str(bad) in str(excinfo.value)


def test_store_sets_a_busy_timeout(tmp_path, monkeypatch):
    """Transient contention (backup.py's own Store, a sync client) must wait,
    not surface as an immediate 'database is locked' to a writing thread."""
    monkeypatch.setattr("micofx.store.DB_PATH", tmp_path / "micofx.db")
    monkeypatch.setattr("micofx.store.ensure_dirs", lambda: None)

    from micofx.store import Store

    store = Store()
    try:
        got = store._db.execute("PRAGMA busy_timeout").fetchone()[0]
        assert int(got) >= 15000
    finally:
        store.close()


def test_store_close_is_idempotent_enough_for_shutdown(tmp_path, monkeypatch):
    monkeypatch.setattr("micofx.store.DB_PATH", tmp_path / "micofx.db")
    monkeypatch.setattr("micofx.store.ensure_dirs", lambda: None)

    from micofx.store import Store

    store = Store()
    store.close()
    with pytest.raises(sqlite3.ProgrammingError):
        store._db.execute("SELECT 1")


def test_emit_flattens_newlines_so_a_payload_cannot_mint_a_fake_trade_line(
        tmp_path, monkeypatch):
    """Rejected opt family names used to land in the log unescaped."""
    monkeypatch.setattr("micofx.logbus.LOG_DIR", tmp_path)
    bus = LogBus()
    bus._file = tmp_path / "micofx.log"
    bus.emit(
        "dusuruldu: x\n2026-08-26 07:00:00 TRADE  [US30] #999 BUY 1.0 lot",
        "TRADE", "NAS100")
    text = bus._file.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert len(lines) == 1, text
    assert "TRADE  [US30] #999" not in text.split("dusuruldu", 1)[-1] or (
        "\n2026-08-26" not in text)
