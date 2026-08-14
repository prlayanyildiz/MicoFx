"""Every fill was filed under the primary leg, including the secondary's.

``_cycle`` tallied an entry after ``_try_entry`` returned, and read the leg off
the state at that moment::

    self._try_entry(cfg, state, account)
    self._tally_entry(cfg.symbol, state.entry_block,
                      bar_key=state.pending_bar_key,
                      source=state.signal_source)

But the successful-fill path inside ``_try_entry`` clears the signal it just
consumed - ``state.signal_source = ""`` - a few lines before setting
``entry_block = "acildi"``. By the time the tally read it the source was gone,
and ``_tally_entry`` resolves an empty source to ``primary``. A refusal returns
long before that clearing, which is why blocks were attributed correctly and
only fills were not.

Measured on the live book over the counter's own window, which starts
2026-08-11 12:28 and survives restarts:

    leg         fills in the log    panel "opened"
    primary                   66                65
    secondary                 25                 0

Twenty-five secondary fills, every one of them lost, while primary lines up
almost exactly over the same window - and the per-symbol excess in primary is
where they went (JPN225 +6 against 8 secondary fills, US30 +2 against 4,
GER40 +1 against 3).

The damage is not the total. ``fill_rate`` is per leg and the panel exists to
say which leg a gate is eating, so the one leg it could never vindicate was the
one it was built to examine. DECISIONS 6 - "the secondary leg opens nothing,
structural rather than a bug" - was concluded from this column, and both
scanners repeated it for rounds.

The leg is now read before the call. ``_try_entry`` decides which leg to act on
from exactly that value on entry (``secondary = state.signal_source ==
"secondary"``), so the pre-call source is the correct attribution for a fill and
a refusal alike.

The first test asserts the ordering in engine.py's own text. Driving the real
_cycle would need the broker client, the supervisor and an account snapshot
stubbed, and a test that rebuilt the caller's three lines in Python would be
asserting on its own copy rather than on the engine - which is the trap this
defect was hiding behind in the first place. The rest assert the tally's
behaviour directly.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine

ENGINE_SRC = (Path(__file__).resolve().parents[1]
              / "micofx" / "engine.py").read_text(encoding="utf-8")


class _Store:
    def __init__(self):
        self.saved = {}
        self.symbols = {s: object() for s in ("GER40", "JPN225", "US500")}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)

    def set_setting(self, key, value):
        self.saved[key] = value


def _engine():
    eng = object.__new__(Engine)
    eng.store = _Store()
    eng._entry_blocks = {}
    eng._entry_last_bar = {}
    eng._entry_blocks_since = 1000.0
    eng._entry_blocks_dirty = False
    return eng


def _row(eng, symbol, leg):
    return next((r for r in eng.entry_blocks()["rows"]
                 if r["symbol"] == symbol and r["leg"] == leg), None)


# ------------------------------------------------------------- the defect

def test_the_leg_is_read_before_the_entry_consumes_the_signal():
    """_try_entry clears signal_source on a fill; reading it after loses the leg."""
    block = ENGINE_SRC[ENGINE_SRC.index("ready.sort(key="):]
    block = block[:block.index("self._flush_entry_blocks()")]

    call = block.index("self._try_entry(")
    tally = block.index("self._tally_entry(")
    assert call < tally, "beklenen sira bozuldu - test kendini gozden gecirmeli"

    after = block[call:tally]
    assert re.search(r"source\s*=\s*state\.signal_source", block[tally:]) is None, (
        "bacak _try_entry'den SONRA okunuyor - dolumda signal_source silinmis oluyor")
    assert re.search(r"=\s*state\.signal_source", block[:call]), (
        "bacak cagri oncesinde yakalanmali")
    assert "state.signal_source" not in after or "source" in after


def test_the_successful_path_still_clears_the_consumed_signal():
    """The clearing itself is correct - the signal has been spent. If it ever
    goes away, reading the leg after the call would start working by accident
    and this defect would look fixed for the wrong reason."""
    assert 'state.signal_source = ""' in ENGINE_SRC


# --------------------------------------------------- the tally's own behaviour

def test_a_retired_source_fill_lands_on_primary():
    """Nothing mints a secondary source any more; the tally must not invent one."""
    eng = _engine()
    eng._tally_entry("GER40", "acildi", bar_key=(1, 0), source="secondary")

    sec = _row(eng, "GER40", "secondary")
    assert sec is None
    assert _row(eng, "GER40", "primary")["opened"] == 1


def test_a_leg_reports_its_own_fill_rate():
    eng = _engine()
    eng._tally_entry("US500", "spread", bar_key=(1, 0), source="secondary")
    eng._tally_entry("US500", "acildi", bar_key=(2, 0), source="secondary")

    row = _row(eng, "US500", "primary")
    assert row["signals"] == 2
    assert row["opened"] == 1
    assert row["fill_rate"] == 0.5
    assert row["blocks"] == {"spread": 1}


def test_an_empty_source_is_still_primary():
    """Unchanged: a symbol with no ensemble has one leg and names it primary."""
    eng = _engine()
    eng._tally_entry("JPN225", "acildi", bar_key=(1, 0), source="")
    assert _row(eng, "JPN225", "primary")["opened"] == 1


def test_the_balance_identity_holds_per_leg():
    """acilis + bloklar == sinyal, checked every scan round."""
    eng = _engine()
    for bar, reason in ((1, "spread"), (2, "acildi"), (3, "ai_gate")):
        eng._tally_entry("US500", reason, bar_key=(bar, 0), source="secondary")

    row = _row(eng, "US500", "primary")
    assert row["opened"] + sum(row["blocks"].values()) == row["signals"]
