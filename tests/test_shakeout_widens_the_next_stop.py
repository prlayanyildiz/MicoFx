"""Next entry widens the hard stop when THIS symbol keeps dying on it.

GER40 27.08: six original-SL deaths before noon, later through_entry.
The search still prefers 1.0 (score buys a tight stop). A hand PATCH to
2.0 is cycle-speed against apply's pending revert. Derive a floor from
autopsies so the next ticket on that symbol is not 1.0 again. Open
tickets keep the stop they were born with.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.risk import shakeout_size_note, shakeout_sl_atr_mult


def _sl(symbol: str, n: int, *, reason: str = "sl", r: float = -1.0) -> list[dict]:
    return [{"symbol": symbol, "exit_reason": reason, "r_realised": r}
            for _ in range(n)]


def test_a_quiet_book_keeps_the_searched_stop():
    assert shakeout_sl_atr_mult(1.0, "GER40", []) == 1.0
    assert shakeout_sl_atr_mult(1.0, "GER40", _sl("GER40", 2)) == 1.0


def test_three_original_sl_deaths_raise_the_floor():
    assert shakeout_sl_atr_mult(1.0, "GER40", _sl("GER40", 3)) == 2.0


def test_another_symbols_deaths_do_not_stain():
    assert shakeout_sl_atr_mult(1.0, "NAS100", _sl("GER40", 6)) == 1.0


def test_a_wide_stop_is_not_pulled_in():
    assert shakeout_sl_atr_mult(2.5, "GER40", _sl("GER40", 6)) == 2.5


def test_trail_and_flatten_are_not_shakeouts():
    rows = _sl("GER40", 2) + _sl("GER40", 3, reason="flatten") + _sl(
        "GER40", 3, reason="trail", r=0.4)
    assert shakeout_sl_atr_mult(1.0, "GER40", rows) == 1.0


def test_a_recovered_window_releases_the_floor():
    rows = _sl("GER40", 6) + _sl("GER40", 10, reason="trail", r=1.2)
    assert shakeout_sl_atr_mult(1.0, "GER40", rows) == 1.0


def test_the_accepted_mix_is_written_on_the_floor():
    """Do not 'complete' the floor by scaling trail to match a 2.0 stop."""
    doc = shakeout_sl_atr_mult.__doc__ or ""
    lowered = doc.lower()
    assert "trail stays at the searched" in lowered
    assert "do not scale trail" in lowered


def test_entry_path_reads_the_floor():
    src = (Path(__file__).resolve().parents[1] / "micofx" / "engine.py"
           ).read_text(encoding="utf-8")
    body = src[src.index("def _try_entry"):]
    assert "shakeout_sl_atr_mult" in body
    assert "shakeout_size_note" in body
    assert body.index("lot_for") < body.index("shakeout_size_note")


def test_the_floor_log_reaches_disk():
    """RISK is not in _PERSIST and the panel does not know it. WARN is both."""
    from micofx.logbus import _PERSIST
    src = (Path(__file__).resolve().parents[1] / "micofx" / "engine.py"
           ).read_text(encoding="utf-8")
    body = src[src.index("def _try_entry"):]
    chunk = body[body.index("shakeout_size_note"): body.index(
        "if lot <= 0")]
    assert '"WARN"' in chunk
    assert '"RISK"' not in chunk
    assert "WARN" in _PERSIST
    assert "RISK" not in _PERSIST


def test_a_free_lot_keeps_dollar_risk():
    assert shakeout_size_note(0.2, "risk %0.8 -> 0.200") == "lot serbest, risk ayni"


def test_a_pinned_lot_doubles_dollar_risk():
    note = "risk %0.8 -> 0.050 (min lot 0.1 riski asiyor, 2.0x)"
    assert shakeout_size_note(0.1, note) == "lot tabanda, gercek risk buyuyor"


def test_a_skipped_lot_says_so():
    note = "min lot 0.1 riski 4.0x asiyor, islem atlandi (risk %0.8 -> 0.020)"
    assert shakeout_size_note(0.0, note) == "islem atlandi"
