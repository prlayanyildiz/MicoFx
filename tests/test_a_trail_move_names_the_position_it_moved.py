"""The trail line said a stop moved, never which position's.

``SL guncellendi -> 68434.85399 (kar 4.38xATR)`` - the level and the profit
that earned it, and nothing to say whose stop it was. JPN225 held five open
positions today and logged two trail moves in the same second; nothing in the
file distinguishes them, so a trail move cannot be paired with the close it
eventually produced.

This is the hole that was already closed once on the entry line, for the same
reason, and engine.py records why beside it:

    The ticket, so an entry can be matched to its own close later. The close
    line has carried it all along; this one did not, and matching them meant
    FIFO by symbol - which silently pairs the wrong two the moment a symbol
    holds more than one position.

The close line carries a ticket and the entry line now does too, so the trail
line was the last of the three still anonymous - and it is the one that answers
whether a winner was trailed out or stopped out, which is the whole of exit
forensics. "Stop ile kapandi" is emitted for both cases, so without this the
only available signal is the sign of the profit.

``pos["ticket"]`` is already in hand at the emit - it is the argument to the
modify_position call on the line above.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ENGINE = (Path(__file__).resolve().parents[1] / "micofx" / "engine.py").read_text(
    encoding="utf-8")


def _trail_emit() -> str:
    i = ENGINE.index("SL guncellendi")
    return ENGINE[ENGINE.rindex("LOG.emit", 0, i):ENGINE.index("\n\n", i)]


# ------------------------------------------------------------- the defect

def test_the_trail_line_carries_the_ticket():
    emit = _trail_emit()
    assert "ticket" in emit, (
        "trail satiri hangi pozisyonun stopunu oynattigini soylemiyor - "
        "bir sembolde birden fazla pozisyon varken eslestirilemez")


def test_it_is_emitted_right_after_the_modify_that_owns_that_ticket():
    """The ticket in the message must be the one that was actually modified."""
    i = ENGINE.index("SL guncellendi")
    before = ENGINE[:i]
    call = before.rindex("self.client.modify_position(")
    assert 'modify_position(pos["ticket"]' in ENGINE[call:call + 60]
    assert ENGINE.count("SL guncellendi") == 1, (
        "ikinci bir trail mesaji cikmis - o da ticket tasimali"
    )


# --------------------------------------------------- what must keep working

def test_the_level_and_the_profit_that_earned_it_are_still_reported():
    emit = _trail_emit()
    assert "target" in emit
    assert "xATR" in emit
    assert "profit_dist" in emit


def test_the_entry_line_still_carries_its_ticket():
    """Fixed in 32db3d3 for this same reason; the trail line is the last of
    the three. If this ever regresses the pairing breaks at the other end."""
    assert re.search(r'f"#\{ticket\}', ENGINE), "giris satiri ticket'ini kaybetmis"


def test_the_close_line_still_carries_its_ticket():
    assert "Stop ile kapandi" in ENGINE or "kapandi" in ENGINE
