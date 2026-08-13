"""A rotation that is interrupted must not take the whole log with it.

_rotate reads the file, keeps the newest half, and used to put it back with
``Path.write_bytes``. That opens for truncate first, so between the truncate and
the end of a two-megabyte write the log is a partial file. A process killed in
that window loses the ENTIRE history - not the old half the rotation set out to
drop.

Its own docstring holds the standard this misses: "an audit trail that silently
loses its past and still looks continuous is worse than one that admits the
gap". The note it writes admits the gap it intends. It could not admit this one,
because there would be nothing left to write it in.

The window is small and rotation is rare - roughly every five weeks at the
current rate, with the live file at 1.1 MB after ten days against a 4 MB limit.
That rarity is the argument for fixing it rather than against: a total loss of
the audit trail, once every few weeks at an unpredictable moment, is the kind of
thing nobody would connect to anything afterwards.

backup.py already solves exactly this, writing to a .part it promotes only once
the archive is complete. The same policy on the other path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import logbus
from micofx.logbus import _MAX_FILE_BYTES, LogBus


@pytest.fixture
def bus(tmp_path, monkeypatch):
    monkeypatch.setattr(logbus, "LOG_DIR", tmp_path)
    b = LogBus()
    b._file = tmp_path / "micofx.log"
    return b


def _oversized(bus) -> None:
    line = b"2026-08-13 04:00:00 TRADE  [GER40] satir\n"
    bus._file.write_bytes(line * ((_MAX_FILE_BYTES // len(line)) + 200))


# ------------------------------------------------------------- the defect

def test_a_failed_rotation_leaves_the_log_intact(bus, monkeypatch):
    """The whole point, and it has to imitate the real failure to mean
    anything.

    A write that raises before touching anything proves nothing - the old code
    survived that too. What actually happens is that the open truncates and the
    write then dies partway, so the stand-in truncates its target first and
    only then raises. Against the old code that target IS the log and it is
    gone; against this one it is the .part and the log has not been opened.
    """
    _oversized(bus)
    before = bus._file.read_bytes()

    def _truncate_then_die(self, data):
        with open(self, "wb"):
            pass                                  # truncate, like the real open
        raise OSError(28, "Diskte yer yok")

    monkeypatch.setattr(Path, "write_bytes", _truncate_then_die)
    bus.emit("tetik", "TRADE", "GER40")          # _write_file swallows OSError

    assert bus._file.read_bytes() == before, (
        "yarim kalan rotasyon logun tamamini goturdu")


def test_the_replacement_is_atomic(bus, monkeypatch):
    """Pinned by behaviour, not by reading the source: the log must never be
    seen empty or short while the new content is being written."""
    seen: list[int] = []
    real = os.replace

    def _spy(src, dst):
        seen.append(Path(dst).stat().st_size if Path(dst).exists() else -1)
        return real(src, dst)

    _oversized(bus)
    monkeypatch.setattr(logbus.os, "replace", _spy)
    bus.emit("tetik", "TRADE", "GER40")

    assert seen, "os.replace kullanilmiyor - yazim atomik degil"
    assert seen[0] > _MAX_FILE_BYTES, (
        "eski dosya replace anina kadar tam boyutunda durmali")


def test_no_part_file_is_left_behind(bus):
    _oversized(bus)
    bus.emit("tetik", "TRADE", "GER40")
    leftovers = [p.name for p in bus._file.parent.glob("*.part")]
    assert leftovers == [], f"artik dosya kaldi: {leftovers}"


# --------------------------------------------------- what must keep working

def test_rotation_still_halves_the_file(bus):
    _oversized(bus)
    bus.emit("tetik", "TRADE", "GER40")
    assert bus._file.stat().st_size < _MAX_FILE_BYTES


def test_it_still_says_history_was_dropped(bus):
    _oversized(bus)
    bus.emit("tetik", "TRADE", "GER40")
    first = bus._file.read_text(encoding="utf-8").splitlines()[0]
    assert "SISTEM" in first and "dusuruldu" in first


def test_it_still_starts_on_a_whole_line(bus):
    _oversized(bus)
    bus.emit("tetik", "TRADE", "GER40")
    for line in bus._file.read_text(encoding="utf-8").splitlines():
        assert line.startswith("2026-"), f"satir ortasindan baslamis: {line[:40]}"
