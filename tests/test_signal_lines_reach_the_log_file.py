"""The line that says WHY an entry fired has to survive the session.

``_PERSIST`` decides which levels reach disk, and SIGNAL was not in it. The
docstring gave one reason for the whole excluded group - "INFO/DEBUG/SIGNAL stay
in memory so a 1-2 second poll loop cannot flood the log file" - and that reason
is about per-poll emission. It is true of INFO and DEBUG. It was never true of
SIGNAL: all three emission sites sit behind a bar gate (``_refresh_signal`` and
``_refresh_secondary_signal`` both return early when the closed bar has not
moved) or fire once on a state transition (the cross-signal skip).

Measured rather than argued: 213 signals over a 38.7 hour window from the
entry-block counters, about 132 lines a day across ten symbols, roughly 11 KB
against a 4 MB rotation limit. Three tenths of one percent of the budget the
exclusion was protecting.

What it cost is specific. A SIGNAL line carries K, D, ATR, ADX and the
higher-timeframe bias as they stood when the bar closed - the only record of
what the strategy was looking at. Every loss review this session could say a
trade opened and nothing about why. The comment beside the emission in engine.py
even said "it is this line the loss reviews read back afterwards", which was not
possible: it never reached disk. The ring buffer holds 1500 entries and is
cleared on restart, and this session restarts several times an hour.

INFO and DEBUG stay excluded, and that is the half of the rule worth keeping.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.logbus import _PERSIST, LogBus


def _bus(tmp_path: Path) -> LogBus:
    bus = LogBus()
    bus._file = tmp_path / "micofx.log"
    return bus


def _written(tmp_path: Path) -> str:
    f = tmp_path / "micofx.log"
    return f.read_text(encoding="utf-8") if f.exists() else ""


# ------------------------------------------------------------- the defect

def test_a_signal_line_is_written_to_disk(tmp_path):
    bus = _bus(tmp_path)
    bus.emit("Sinyal BUY | K=54.0 | D=58.2 | ATR=0.00042 | ADX=22 | HTF=+1",
             "SIGNAL", "JPN225")
    assert "Sinyal BUY" in _written(tmp_path), (
        "girisin NEDEN acildigini soyleyen tek satir diske hic ulasmiyor")
    assert "JPN225" in _written(tmp_path)


def test_signal_is_in_the_persist_set():
    assert "SIGNAL" in _PERSIST


# --------------------------------------------------- the half worth keeping

def test_info_and_debug_still_stay_in_memory(tmp_path):
    """These ARE per-poll, which is what the exclusion was written for."""
    bus = _bus(tmp_path)
    bus.emit("dongu tamam", "INFO")
    bus.emit("ayrinti", "DEBUG")
    assert _written(tmp_path) == ""
    assert "INFO" not in _PERSIST and "DEBUG" not in _PERSIST


def test_the_levels_that_always_persisted_still_do(tmp_path):
    bus = _bus(tmp_path)
    for level in ("WARN", "ERROR", "TRADE", "OPT", "AI"):
        bus.emit(f"{level} satiri", level)
    written = _written(tmp_path)
    for level in ("WARN", "ERROR", "TRADE", "OPT", "AI"):
        assert f"{level} satiri" in written


def test_everything_reaches_the_ring_either_way(tmp_path):
    """Persistence is about the file; the terminal still shows all of it."""
    bus = _bus(tmp_path)
    bus.emit("bellek", "INFO")
    bus.emit("disk", "SIGNAL")
    messages = [e["message"] for e in bus._buf]
    assert "bellek" in messages and "disk" in messages


def test_a_signal_line_carries_its_symbol_and_timestamp(tmp_path):
    """What makes it usable months later, when the ring is long gone."""
    bus = _bus(tmp_path)
    bus.emit("Sinyal SELL | ATR=1.5 | HTF=-1", "SIGNAL", "US30")
    line = _written(tmp_path).strip()
    assert "[US30]" in line
    assert "SIGNAL" in line
    assert line[:2].isdigit(), f"zaman damgasi yok: {line[:40]}"
