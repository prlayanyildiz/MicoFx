"""Rotation must keep whole lines, respect its byte budget, and admit the gap.

The log file is the audit trail an operator opens after an unexplained fill.
Rotation used to slice the decoded text - ``read_text()[-_MAX_FILE_BYTES // 2:]``
- which got three things wrong, all of them observed on a real rotation this
file went through:

  * characters counted against a budget written in bytes, so the result came
    back over its own target;
  * the slice landed at an arbitrary offset, so the file opened with half a
    line: ``di -> 3421.55512 (kar 2.34xATR)``;
  * nothing said history had been dropped, so the log looked continuous
    across a gap it had just created.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import logbus
from micofx.logbus import _MAX_FILE_BYTES, LogBus

ASCII_LINE = ("2026-08-11 03:00:00 TRADE  [XAUUSD] "
              "SL guncellendi -> 3421.55512 (kar 2.34xATR)\n")
TURKISH_LINE = ("2026-08-11 03:00:00 TRADE  [XAUUSD] "
                "Gunluk zarar limiti asildi - islem kapatildi igscou\n")


@pytest.fixture
def bus(tmp_path, monkeypatch):
    monkeypatch.setattr(logbus, "LOG_DIR", tmp_path)
    b = LogBus()
    b._file = tmp_path / "micofx.log"
    b.enable_disk()
    return b


def _overfill(bus, line: str) -> int:
    n = (_MAX_FILE_BYTES // len(line.encode("utf-8"))) + 500
    bus._file.write_text(line * n, encoding="utf-8")
    return bus._file.stat().st_size


def _lines(bus) -> list[str]:
    return [ln for ln in bus._file.read_text(encoding="utf-8").split("\n") if ln]


@pytest.mark.parametrize("line", [ASCII_LINE, TURKISH_LINE],
                         ids=["ascii", "turkce"])
def test_rotation_keeps_only_whole_lines(bus, line):
    before = _overfill(bus, line)
    assert before > _MAX_FILE_BYTES

    bus.emit("tetik", "TRADE", "TEST")

    lines = _lines(bus)
    # Every surviving line is a real log line, including the first one.
    assert all(ln.startswith("2026-") for ln in lines), lines[0][:80]


@pytest.mark.parametrize("line", [ASCII_LINE, TURKISH_LINE],
                         ids=["ascii", "turkce"])
def test_rotation_respects_its_byte_budget(bus, line):
    _overfill(bus, line)
    bus.emit("tetik", "TRADE", "TEST")

    size = bus._file.stat().st_size
    # Half the cap, plus the notice line and the entry that triggered it.
    assert size <= _MAX_FILE_BYTES // 2 + 1024, size


def test_rotation_leaves_a_notice_that_history_was_dropped(bus):
    _overfill(bus, ASCII_LINE)
    bus.emit("tetik", "TRADE", "TEST")

    first = _lines(bus)[0]
    assert "WARN" in first
    assert "sinirini asti" in first
    assert "dusuruldu" in first


def test_rotation_does_not_corrupt_utf8(bus):
    """A byte slice that ignored line boundaries could also split a character."""
    line = ("2026-08-11 03:00:00 TRADE  [XAUUSD] "
            "Gunluk zarar limiti asildi — islem kapatildi ığşçöü\n")
    _overfill(bus, line)
    bus.emit("tetik", "TRADE", "TEST")

    raw = bus._file.read_bytes()
    text = raw.decode("utf-8")          # strict: no errors= fallback
    assert "�" not in text


def test_the_triggering_entry_survives_rotation(bus):
    _overfill(bus, ASCII_LINE)
    bus.emit("bu satir kalmali", "TRADE", "TEST")

    assert "bu satir kalmali" in _lines(bus)[-1]


def test_a_small_file_is_not_rotated(bus):
    bus.emit("birinci", "TRADE")
    bus.emit("ikinci", "TRADE")

    lines = _lines(bus)
    assert len(lines) == 2
    assert "sinirini asti" not in bus._file.read_text(encoding="utf-8")


def test_non_persisted_levels_never_reach_disk(bus):
    """INFO and DEBUG only. SIGNAL used to be listed here too, on the same
    flood argument - and that argument is about per-poll emission, which these
    two are and SIGNAL is not: it fires behind a bar gate, about 132 lines a
    day. See test_signal_lines_reach_the_log_file.py."""
    bus.emit("gorunmez", "INFO")
    bus.emit("gorunmez", "DEBUG")

    assert not bus._file.exists() or bus._file.read_text(encoding="utf-8") == ""


def test_rotation_survives_a_file_of_one_enormous_line(bus):
    """No newline anywhere: the boundary search must not keep a partial line."""
    bus._file.write_bytes(b"x" * (_MAX_FILE_BYTES + 4096))

    bus.emit("tetik", "TRADE", "TEST")

    lines = _lines(bus)
    assert all(ln.startswith("2026-") for ln in lines)
    assert bus._file.stat().st_size < _MAX_FILE_BYTES
